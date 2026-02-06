import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Piano Scout Manager", layout="wide")

# CSS Personalizado
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
    st.success("Status atualizado!")
    st.cache_data.clear()

def salvar_csv_editado(df_novo):
    try:
        df_novo.to_csv(CSV_PATH, index=False)
        st.success("CSV Atualizado!")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar CSV: {e}")

# --- PROCESSAMENTO ---
if not os.path.exists(DB_PATH) or not os.path.exists(CSV_PATH):
    st.error("Dados não encontrados.")
    st.stop()

df_precos = carregar_dados()
df_ref_full = pd.read_csv(CSV_PATH)

df_precos['modelo_key'] = df_precos['modelo'].astype(str).str.strip().str.upper()
df_ref_full['modelo_key'] = df_ref_full['modelo'].astype(str).str.strip().str.upper()

df_full = pd.merge(df_precos, df_ref_full, on='modelo_key', how='left', suffixes=('', '_csv'))
df_full['custo_total'] = df_full['preco'] + df_full['custo_reparo']
df_full['ativo'] = df_full['ativo'].apply(lambda x: x in [1, '1', True, 'True'])

# Filtro: Ativos com Score > 50
df_ativos = df_full[(df_full['ativo'] == True) & (df_full['score_geral'] > 50)].copy()

stats_mercado = df_ativos.groupby('modelo_key')['custo_total'].agg(
    Minimo='min', Maximo='max', Qtd='count'
).reset_index()

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Matriz de Decisão", "📝 Gestão de Anúncios", "📚 Editor AHSD (CSV)"])

with tab1:
    col_grafico, col_detalhes = st.columns([3, 1])

    with col_grafico:
        if not df_ativos.empty:
            # Melhor preço por modelo
            idx_melhores = df_ativos.groupby('modelo_key')['custo_total'].idxmin()
            df_plot = df_ativos.loc[idx_melhores].copy().reset_index(drop=True)

            # Cálculo dos Quadrantes
            min_score, max_score = df_plot['score_geral'].min(), df_plot['score_geral'].max()
            min_custo, max_custo = df_plot['custo_total'].min(), df_plot['custo_total'].max()
            
            div_x = ((max_score - min_score) / 2) + min_score
            div_y = ((max_custo - min_custo) / 2) + min_custo
            
            margem_x = (max_score - min_score) * 0.15 if max_score != min_score else 5
            margem_y = (max_custo - min_custo) * 0.15 if max_custo != min_custo else 500

            df_plot['tamanho_fixo'] = 12
            df_plot['cor_legenda'] = df_plot.apply(
                lambda x: '⭐ PRIORIDADE' if str(x['priorizado']).lower() in ['true', 'sim'] else x['condicao'], axis=1
            )

            # GRÁFICO
            fig = px.scatter(
                df_plot, x="score_geral", y="custo_total", color="cor_legenda",
                color_discrete_map={"⭐ PRIORIDADE": "#FFD700", "Novo": "#2E86C1", "Usado": "#28B463"},
                size="tamanho_fixo", size_max=12,
                hover_name="modelo", text="modelo", height=700,
                custom_data=['modelo_key'],
                labels={"score_geral": "Qualidade (Score)", "custo_total": "Preço Total (R$)"}
            )

            fig.update_traces(textposition='top center')

            # Pintura dos Quadrantes (Semântica)
            fig.update_layout(
                shapes=[
                    # VERDE (Inf. Dir): Alta Qualidade, Baixo Preço (IDEAL)
                    dict(type="rect", xref="x", yref="y", x0=div_x, x1=max_score + margem_x, y0=min_custo - margem_y, y1=div_y, 
                         fillcolor="rgba(46, 204, 113, 0.2)", layer="below", line_width=0),
                    # AZUL (Sup. Dir): Alta Qualidade, Preço Alto (PREMIUM)
                    dict(type="rect", xref="x", yref="y", x0=div_x, x1=max_score + margem_x, y0=div_y, y1=max_custo + margem_y, 
                         fillcolor="rgba(52, 152, 219, 0.15)", layer="below", line_width=0),
                    # AMARELO (Inf. Esq): Baixa Qualidade, Preço Baixo (ENTRADA)
                    dict(type="rect", xref="x", yref="y", x0=min_score - margem_x, x1=div_x, y0=min_custo - margem_y, y1=div_y, 
                         fillcolor="rgba(241, 196, 15, 0.15)", layer="below", line_width=0),
                    # VERMELHO (Sup. Esq): Baixa Qualidade, Preço Alto (EVITAR)
                    dict(type="rect", xref="x", yref="y", x0=min_score - margem_x, x1=div_x, y0=div_y, y1=max_custo + margem_y, 
                         fillcolor="rgba(231, 76, 60, 0.2)", layer="below", line_width=0),
                ],
                annotations=[
                    dict(x=max_score, y=min_custo, text="✨ OPORTUNIDADE", showarrow=False, font=dict(color="green", size=14), yanchor="bottom"),
                    dict(x=max_score, y=max_custo, text="💎 PREMIUM", showarrow=False, font=dict(color="blue", size=14), yanchor="top"),
                    dict(x=min_score, y=min_custo, text="⚠️ ENTRADA", showarrow=False, font=dict(color="orange", size=14), yanchor="bottom"),
                    dict(x=min_score, y=max_custo, text="🚫 EVITAR", showarrow=False, font=dict(color="red", size=14), yanchor="top")
                ],
                yaxis=dict(range=[min_custo - margem_y, max_custo + margem_y], gridcolor='rgba(0,0,0,0.05)'),
                xaxis=dict(range=[min_score - margem_x, max_score + margem_x], gridcolor='rgba(0,0,0,0.05)'),
                title="<b>Matriz de Decisão AHSD: Qualidade vs Investimento</b>"
            )

            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")
        else:
            st.warning("Sem dados suficientes.")
            event = None

    with col_detalhes:
        selected_key = None
        if event and len(event['selection']['points']) > 0:
            selected_key = event['selection']['points'][0]['customdata'][0]
        elif not df_plot.empty:
             selected_key = df_plot.loc[df_plot['score_geral'].idxmax()]['modelo_key']
        
        if selected_key:
            row = df_plot[df_plot['modelo_key'] == selected_key].iloc[0]
            st.markdown(f"### {row['modelo']}")
            st.markdown(f"💰 **R$ {row['custo_total']:.0f}**")
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box'><div class='metric-label'>Mecânica</div><div class='metric-value'>{row['mecanica']}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-label'>Som</div><div class='metric-value'>{row['som_polifonia']}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-label'>Score</div><div class='metric-value'>{row['score_geral']:.0f}</div></div>", unsafe_allow_html=True)
            st.info(row['justificativa'])
            st.link_button("🔗 Ver Anúncio", row['link'], use_container_width=True)

with tab2:
    st.header("Gestão de Anúncios")
    cols_gestao = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link']
    df_editor_db = st.data_editor(
        df_precos[cols_gestao],
        column_config={"ativo": st.column_config.CheckboxColumn("Ativo?"), "link": st.column_config.LinkColumn("Link")},
        hide_index=True, disabled=["id", "data_consulta", "modelo", "link"], key="editor_db"
    )
    if st.button("💾 Salvar DB"): salvar_alteracoes_db(df_editor_db)

with tab3:
    st.header("📚 Editor CSV (Régua Técnica)")
    df_editor_csv = st.data_editor(df_ref_full, hide_index=True, use_container_width=True, key="editor_csv")
    if st.button("💾 Salvar CSV"):
        df_para_salvar = df_editor_csv.copy()
        if 'modelo_key' in df_para_salvar.columns: df_para_salvar.drop(columns=['modelo_key'], inplace=True)
        salvar_csv_editado(df_para_salvar)