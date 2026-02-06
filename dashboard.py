import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Piano Scout Manager", layout="wide")

# CSS Personalizado (Estilo Limpo)
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #4CAF50; }
    
    div[data-testid="stVerticalBlock"] > div[data-testid="column"]:nth-of-type(2) {
        background-color: #f8f9fa;
        border-left: 1px solid #ddd;
        padding: 20px;
        border-radius: 8px;
    }
    
    .metric-box {
        text-align: center;
        background: white;
        padding: 8px;
        border-radius: 5px;
        border: 1px solid #eee;
        margin-bottom: 5px;
    }
    .metric-label { font-size: 12px; color: #666; text-transform: uppercase; }
    .metric-value { font-size: 16px; font-weight: bold; color: #333; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

# --- FUNÇÕES DE DADOS ---

def carregar_dados():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM precos", conn)
    conn.close()
    return df

def salvar_alteracoes_db(df_editado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for index, row in df_editado.iterrows():
        cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (row['ativo'], row['id']))
    conn.commit()
    conn.close()
    st.success("Status dos anúncios atualizado no Banco de Dados!")
    st.cache_data.clear()

def salvar_csv_editado(df_novo):
    try:
        df_novo.to_csv(CSV_PATH, index=False)
        st.success("Arquivo 'modelos_alvo.csv' atualizado com sucesso!")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar o CSV: {e}")

def media_geometrica(series):
    arr = np.array(series)
    arr = arr[arr > 0]
    if len(arr) == 0: return 0
    return np.exp(np.mean(np.log(arr)))

# --- CARREGAMENTO ---
if not os.path.exists(DB_PATH) or not os.path.exists(CSV_PATH):
    st.error("Arquivos de dados não encontrados.")
    st.stop()

df_precos = carregar_dados()
df_ref = pd.read_csv(CSV_PATH)

# Padronização para Merge
df_precos['modelo_key'] = df_precos['modelo'].astype(str).str.strip().str.upper()
df_ref['modelo_key'] = df_ref['modelo'].astype(str).str.strip().str.upper()

if 'priorizado' not in df_ref.columns:
    df_ref['priorizado'] = False

df_full = pd.merge(df_precos, df_ref, on='modelo_key', how='left', suffixes=('', '_csv'))
if 'modelo_csv' in df_full.columns:
    df_full.drop(columns=['modelo_csv'], inplace=True)

df_full['data_consulta'] = pd.to_datetime(df_full['data_consulta'])
df_full['custo_total'] = df_full['preco'] + df_full['custo_reparo']
df_full['justificativa'] = df_full['justificativa'].fillna("Sem avaliação técnica registrada.")
df_full['ativo'] = df_full['ativo'].apply(lambda x: x in [1, '1', True, 'True'])
df_ativos = df_full[df_full['ativo'] == True].copy()

stats_mercado = df_ativos.groupby('modelo_key')['custo_total'].agg(
    Minimo='min',
    Maximo='max',
    MediaGeo=media_geometrica,
    Qtd='count'
).reset_index()

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Análise Gráfica", "📝 Gestão de Anúncios", "📚 Tabela de Avaliações (CSV)"])

with tab1:
    col_grafico, col_detalhes = st.columns([3, 1])

    with col_grafico:
        df_ativos['cor_legenda'] = df_ativos.apply(
            lambda x: '⭐ PRIORIDADE' if str(x['priorizado']).lower() in ['true', 'sim'] else x['condicao'], 
            axis=1
        )
        df_ativos['metrica_tamanho'] = df_ativos['score_geral'] / (df_ativos['custo_total'] + 0.01)

        idx_melhores = df_ativos.groupby('modelo_key')['custo_total'].idxmin()
        df_plot = df_ativos.loc[idx_melhores].copy().reset_index(drop=True)

        if not df_plot.empty:
            min_score, max_score = df_plot['score_geral'].min(), df_plot['score_geral'].max()
            min_custo, max_custo = df_plot['custo_total'].min(), df_plot['custo_total'].max()
            div_x = ((max_score - min_score) / 2) + min_score
            div_y = ((max_custo - min_custo) / 2) + min_custo
            margem_x = (max_score - min_score) * 0.1 if max_score != min_score else 10
            margem_y = (max_custo - min_custo) * 0.1 if max_custo != min_custo else 500
            
            fig = px.scatter(
                df_plot, x="score_geral", y="custo_total", color="cor_legenda",
                color_discrete_map={"⭐ PRIORIDADE": "#FFD700", "Novo": "#2E86C1", "Usado": "#28B463"},
                size=df_plot['metrica_tamanho'].fillna(1),
                hover_name="modelo", text="modelo", height=600,
                custom_data=['modelo_key'] 
            )
            fig.update_traces(textposition='top center')
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                yaxis=dict(range=[max_custo + margem_y, min_custo - margem_y], title="Custo Total (R$)"),
                xaxis=dict(range=[min_score - margem_x, max_score + margem_x], title="Score Geral"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")
        else:
            st.warning("Sem dados ativos.")
            event = None

    with col_detalhes:
        selected_key = None
        if event and len(event['selection']['points']) > 0:
            selected_key = event['selection']['points'][0]['customdata'][0]
        elif not df_plot.empty:
             selected_key = df_plot.loc[df_plot['metrica_tamanho'].idxmax()]['modelo_key']
        
        if selected_key:
            row = df_plot[df_plot['modelo_key'] == selected_key].iloc[0]
            stats = stats_mercado[stats_mercado['modelo_key'] == selected_key].iloc[0]
            st.markdown(f"### {row['modelo']}")
            st.markdown(f"💰 **R$ {row['custo_total']:.0f}**")
            st.caption(f"Mercado: R$ {stats['Minimo']:.0f} - {stats['Maximo']:.0f}")
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box'><div class='metric-label'>Mecânica</div><div class='metric-value'>{row['mecanica']}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-label'>Som</div><div class='metric-value'>{row['som_polifonia']}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-label'>Score</div><div class='metric-value'>{row['score_geral']:.0f}</div></div>", unsafe_allow_html=True)
            st.info(row['justificativa'])
            st.link_button("🔗 Ver Anúncio", row['link'], use_container_width=True)
        else:
            st.info("Nenhum dado selecionado.")

with tab2:
    st.header("Gestão de Anúncios (Banco de Dados)")
    cols_gestao = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link']
    df_editor_db = st.data_editor(
        df_precos[cols_gestao],
        column_config={
            "ativo": st.column_config.CheckboxColumn("Ativo?", default=True),
            "link": st.column_config.LinkColumn("Link"),
            "preco": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
        },
        hide_index=True, disabled=["id", "data_consulta", "modelo", "link"], key="editor_db"
    )
    if st.button("💾 Atualizar Status no Banco"):
        salvar_alteracoes_db(df_editor_db)

with tab3:
    st.header("📚 Editor do Arquivo de Modelos (CSV)")
    st.markdown("Edite as configurações técnicas dos modelos abaixo e salve para atualizar o arquivo físico.")
    
    # Exibe todas as colunas do CSV para edição completa
    df_editor_csv = st.data_editor(
        df_ref,
        column_config={
            "modelo": st.column_config.TextColumn("Nome do Modelo", disabled=True),
            "priorizado": st.column_config.CheckboxColumn("⭐ Prioridade"),
            "score_geral": st.column_config.NumberColumn("Score Total", min_value=0, max_value=100),
            "mecanica": st.column_config.NumberColumn("Mecânica", min_value=0, max_value=100),
            "som_polifonia": st.column_config.NumberColumn("Som", min_value=0, max_value=100),
            "justificativa": st.column_config.TextColumn("Avaliação Técnica", width="large"),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic", # Permite adicionar novos modelos se desejar
        key="editor_csv"
    )

    if st.button("💾 Salvar Alterações no Arquivo CSV"):
        # Removemos a coluna modelo_key antes de salvar para manter o CSV limpo
        df_para_salvar = df_editor_csv.copy()
        if 'modelo_key' in df_para_salvar.columns:
            df_para_salvar.drop(columns=['modelo_key'], inplace=True)
        
        salvar_csv_editado(df_para_salvar)