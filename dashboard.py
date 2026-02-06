import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# Configuração da Página
st.set_page_config(page_title="Piano Scout Manager", layout="wide")

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

def carregar_dados():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM precos", conn)
    conn.close()
    return df

def salvar_alteracoes(df_editado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Atualiza o status 'ativo' no banco
    for index, row in df_editado.iterrows():
        cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (row['ativo'], row['id']))
    conn.commit()
    conn.close()
    st.success("Alterações salvas com sucesso!")
    st.cache_data.clear()

# --- CARREGAMENTO INICIAL ---
if not os.path.exists(DB_PATH) or not os.path.exists(CSV_PATH):
    st.error("Arquivos de dados não encontrados.")
    st.stop()

df_precos = carregar_dados()
df_ref = pd.read_csv(CSV_PATH)

# Garante que a coluna 'priorizado' existe no CSV (trata erro se não existir)
if 'priorizado' not in df_ref.columns:
    df_ref['priorizado'] = False

# Merge dos dados
df_full = pd.merge(df_precos, df_ref, on='modelo', how='left')
df_full['data_consulta'] = pd.to_datetime(df_full['data_consulta'])

# Calcula Custo Total (Preço + Reparo)
df_full['custo_total'] = df_full['preco'] + df_full['custo_reparo']

# Filtra apenas ativos para a ANÁLISE (mas mostra tudo na gestão)
df_ativos = df_full[df_full['ativo'] == 1].copy()

# --- INTERFACE ---
tab1, tab2 = st.tabs(["📊 Análise de Oportunidades", "📝 Gestão da Base de Dados"])

# --- ABA 1: GRÁFICOS ---
with tab1:
    st.title("Cockpit de Inteligência")
    
    # Lógica de Cores Personalizada
    # Priorizados = Dourado, Normais = Azul
    df_ativos['cor_legenda'] = df_ativos.apply(
        lambda x: '⭐ PRIORIDADE' if x['priorizado'] == True or str(x['priorizado']).lower() == 'sim' else x['condicao'], 
        axis=1
    )
    
    # Índice R$/Score para o Mouseover
    df_ativos['indice_custo_beneficio'] = df_ativos['custo_total'] / df_ativos['score_geral']
    
    # Tamanho da bolha (foco no menor preço)
    df_ativos['tamanho_bolha'] = (1 / df_ativos['indice_custo_beneficio']) * 50

    fig = px.scatter(
        df_ativos,
        x="score_geral",
        y="custo_total",
        color="cor_legenda",
        color_discrete_map={
            "⭐ PRIORIDADE": "#FFD700", # Dourado
            "Novo": "#2E86C1",        # Azul
            "Usado": "#28B463"        # Verde
        },
        size="tamanho_bolha",
        hover_name="modelo",
        hover_data={
            "tamanho_bolha": False,
            "cor_legenda": False,
            "estado_detalhado": True,
            "custo_reparo": ":.2f",
            "indice_custo_beneficio": ":.2f",
            "custo_total": ":.2f"
        },
        text="modelo",
        title="Dispersão: Score x Valor Total (Inclui Reparos)",
        height=600
    )
    
    fig.update_traces(textposition='top center')
    fig.update_layout(yaxis=dict(autorange="reversed")) # Menor preço no topo
    st.plotly_chart(fig, use_container_width=True)
    
    st.info("Nota: O valor exibido considera Preço Anunciado + Custo Estimado de Reparo.")

# --- ABA 2: GESTÃO ---
with tab2:
    st.header("Gestão de Anúncios")
    st.markdown("Desmarque a caixa **'ativo'** para remover itens vendidos ou irreais da análise.")
    
    # Editor de Dados
    # Mostramos colunas essenciais
    cols_gestao = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link', 'ai_analise']
    
    df_editor = st.data_editor(
        df_precos[cols_gestao],
        column_config={
            "ativo": st.column_config.CheckboxColumn(
                "Ativo?",
                help="Desmarque para esconder da análise",
                default=True,
            ),
            "link": st.column_config.LinkColumn("Link"),
            "preco": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
        },
        hide_index=True,
        disabled=["id", "data_consulta", "modelo", "link"], # Bloqueia edição do que é fixo
        key="editor_dados"
    )
    
    if st.button("💾 Salvar Alterações no Banco de Dados"):
        salvar_alteracoes(df_editor)