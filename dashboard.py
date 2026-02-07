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
    .metric-label { font-size: 10px; color: #666; text-transform: uppercase; }
    .metric-value { font-size: 14px; font-weight: bold; color: #333; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

# --- INICIALIZAÇÃO DE ESTADO (FILTROS PERSISTENTES) ---
if 'filtro_score' not in st.session_state:
    st.session_state.filtro_score = (50, 100)

if 'filtro_preco' not in st.session_state:
    st.session_state.filtro_preco = (1500.0, 30000.0)

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

def atualizar_status_individual(id_anuncio, novo_status):
    """Atualiza o status de um único item instantaneamente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Converte booleano para 1 ou 0
    valor_db = 1 if novo_status else 0
    cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (valor_db, id_anuncio))
    conn.commit()
    conn.close()
    st.cache_data.clear() # Limpa o cache para o gráfico atualizar

def salvar_csv_editado(df_novo):
    try:
        df_novo.to_csv(CSV_PATH, index=False)
        st.success("CSV Atualizado!")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar CSV: {e}")

def media_geometrica(series):
    arr = np.array(series)
    arr = arr[arr > 0]
    if len(arr) == 0: return 0
    return np.exp(np.mean(np.log(arr)))

# --- PROCESSAMENTO ---
if not os.path.exists(DB_PATH) or not os.path.exists(CSV_PATH):
    st.error("Dados não encontrados. Rode o main.py primeiro.")
    st.stop()

try:
    df_precos = carregar_dados()
    df_ref_full = pd.read_csv(CSV_PATH, on_bad_lines='skip')
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

df_precos['modelo_key'] = df_precos['modelo'].astype(str).str.strip().str.upper()
df_ref_full['modelo_key'] = df_ref_full['modelo'].astype(str).str.strip().str.upper()

df_full = pd.merge(df_precos, df_ref_full, on='modelo_key', how='left', suffixes=('', '_csv'))
df_full['custo_total'] = df_full['preco'] + df_full['custo_reparo']
df_full['ativo'] = df_full['ativo'].apply(lambda x: x in [1, '1', True, 'True'])

# Base bruta de ativos
df_ativos_raw = df_full[df_full['ativo'] == True].copy()

# Estatísticas Gerais
stats_mercado = df_ativos_raw.groupby('modelo_key')['custo_total'].agg(
    Minimo='min', 
    Maximo='max', 
    MediaGeo=media_geometrica, 
    Qtd='count'
).reset_index()

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Matriz de Decisão", "📝 Gestão de Anúncios", "📚 Editor AHSD (CSV)"])

with tab1:
    # --- ÁREA DE FILTROS ---
    with st.expander("🎛️ Filtros de Visualização (Persistentes)", expanded=False):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.session_state.filtro_score = st.slider(
                "Faixa de Score (Qualidade Técnica)",
                min_value=0, max_value=100,
                value=st.session_state.filtro_score,
                key="slider_score"
            )
        with c_f2:
            max_price_db = int(df_ativos_raw['custo_total'].max()) if not df_ativos_raw.empty else 50000
            st.session_state.filtro_preco = st.slider(
                "Faixa de Preço Total (R$)",
                min_value=0.0, max_value=float(max_price_db),
                value=st.session_state.filtro_preco,
                step=100.0,
                key="slider_preco"
            )

    # Aplicação dos Filtros
    min_s, max_s = st.session_state.slider_score
    min_p, max_p = st.session_state.slider_preco
    
    df_plot_filtered = df_ativos_raw[
        (df_ativos_raw['score_geral'] >= min_s) & 
        (df_ativos_raw['score_geral'] <= max_s) &
        (df_ativos_raw['custo_total'] >= min_p) &
        (df_ativos_raw['custo_total'] <= max_p)
    ].copy()

    col_grafico, col_detalhes = st.columns([3, 1])

    with col_grafico:
        if not df_plot_filtered.empty:
            idx_melhores = df_plot_filtered.groupby('modelo_key')['custo_total'].idxmin()
            df_plot = df_plot_filtered.loc[idx_melhores].copy().reset_index(drop=True)

            min_score_g, max_score_g = df_plot['score_geral'].min(), df_plot['score_geral'].max()
            min_custo_g, max_custo_g = df_plot['custo_total'].min(), df_plot['custo_total'].max()
            
            if min_score_g == max_score_g: margem_x = 5
            else: margem_x = (max_score_g - min_score_g) * 0.15
            
            if min_custo_g == max_custo_g: margem_y = 500
            else: margem_y = (max_custo_g - min_custo_g) * 0.15

            div_x = ((max_score_g - min_score_g) / 2) + min_score_g
            div_y = ((max_custo_g - min_custo_g) / 2) + min_custo_g

            df_plot['tamanho_fixo'] = 12
            df_plot['cor_legenda'] = df_plot.apply(
                lambda x: '⭐ PRIORIDADE' if str(x['priorizado']).lower() in ['true', 'sim'] else x['condicao'], axis=1
            )

            fig = px.scatter(
                df_plot, x="score_geral", y="custo_total", color="cor_legenda",
                color_discrete_map={"⭐ PRIORIDADE": "#FFD700", "Novo": "#2E86C1", "Usado": "#28B463"},
                size="tamanho_fixo", size_max=12,
                hover_name="modelo", text="modelo", height=700,
                custom_data=['modelo_key'],
                labels={"score_geral": "Qualidade (Score)", "custo_total": "Preço Total (R$)"}
            )

            fig.update_traces(textposition='top center')

            fig.update_layout(
                shapes=[
                    dict(type="rect", xref="x", yref="y", x0=div_x, x1=max_score_g + margem_x, y0=min_custo_g - margem_y, y1=div_y, 
                         fillcolor="rgba(46, 204, 113, 0.2)", layer="below", line_width=0),
                    dict(type="rect", xref="x", yref="y", x0=div_x, x1=max_score_g + margem_x, y0=div_y, y1=max_custo_g + margem_y, 
                         fillcolor="rgba(52, 152, 219, 0.15)", layer="below", line_width=0),
                    dict(type="rect", xref="x", yref="y", x0=min_score_g - margem_x, x1=div_x, y0=min_custo_g - margem_y, y1=div_y, 
                         fillcolor="rgba(241, 196, 15, 0.15)", layer="below", line_width=0),
                    dict(type="rect", xref="x", yref="y", x0=min_score_g - margem_x, x1=div_x, y0=div_y, y1=max_custo_g + margem_y, 
                         fillcolor="rgba(231, 76, 60, 0.2)", layer="below", line_width=0),
                ],
                annotations=[
                    dict(x=max_score_g, y=min_custo_g, text="✨ OPORTUNIDADE", showarrow=False, font=dict(color="green", size=14), yanchor="bottom"),
                    dict(x=max_score_g, y=max_custo_g, text="💎 PREMIUM", showarrow=False, font=dict(color="blue", size=14), yanchor="top"),
                    dict(x=min_score_g, y=min_custo_g, text="⚠️ ENTRADA", showarrow=False, font=dict(color="orange", size=14), yanchor="bottom"),
                    dict(x=min_score_g, y=max_custo_g, text="🚫 EVITAR", showarrow=False, font=dict(color="red", size=14), yanchor="top")
                ],
                yaxis=dict(range=[min_custo_g - margem_y, max_custo_g + margem_y], gridcolor='rgba(0,0,0,0.05)'),
                xaxis=dict(range=[min_score_g - margem_x, max_score_g + margem_x], gridcolor='rgba(0,0,0,0.05)'),
                title="<b>Matriz de Decisão AHSD: Qualidade vs Investimento</b>"
            )

            # --- CORREÇÃO AQUI: Troquei use_container_width=True por width="stretch" ---
            event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points")
        else:
            st.warning("Nenhum modelo encontrado dentro da faixa de filtros selecionada.")
            event = None

    # --- PAINEL LATERAL APRIMORADO ---
    with col_detalhes:
        selected_key = None
        # Lógica de seleção (mantida)
        if event and len(event['selection']['points']) > 0:
            selected_key = event['selection']['points'][0]['customdata'][0]
        elif not df_plot.empty:
             selected_key = df_plot.loc[df_plot['score_geral'].idxmax()]['modelo_key']
        
        if selected_key:
            row = df_plot[df_plot['modelo_key'] == selected_key].iloc[0]
            stats = stats_mercado[stats_mercado['modelo_key'] == selected_key].iloc[0]
            
            # --- TÍTULO E PREÇO ---
            st.markdown(f"### {row['modelo']}")
            st.markdown(f"💰 **R$ {row['custo_total']:.0f}**")
            
            # --- NOVO CONTROLE DE ATIVAÇÃO ---
            st.write("") # Espaçamento
            
            # O Toggle reflete o estado atual. Se o usuário mudar, executa o if.
            # Usamos uma key única baseada no ID para não confundir o Streamlit
            ativo_toggle = st.toggle(
                "✅ Anúncio Ativo no Gráfico", 
                value=True, # Se está aparecendo aqui, é porque está True no DB
                key=f"toggle_{row['id']}"
            )
            
            if not ativo_toggle: # Se o usuário DESMARCAR
                atualizar_status_individual(row['id'], False)
                st.toast(f"🚫 Anúncio removido: {row['modelo']}", icon="🗑️")
                import time
                time.sleep(0.5) # Pequena pausa para processar
                st.rerun() # Recarrega a página e o ponto some
            
            # --- DADOS DETALHADOS ---
            st.markdown(f"🏬 **Loja:** {row.get('loja', 'Não Inf.')}")
            estado_fmt = str(row.get('estado_detalhado', '')).replace('_', ' ').title()
            st.markdown(f"🏷️ **Estado:** {estado_fmt}")
            
            st.markdown(f"📈 **Máximo:** R$ {stats['Maximo']:,.0f}")
            st.markdown(f"📐 **Média Geo:** R$ {stats['MediaGeo']:,.0f}")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box'><div class='metric-label'>Mecânica</div><div class='metric-value'>{row['mecanica']}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'><div class='metric-label'>Som</div><div class='metric-value'>{row['som_polifonia']}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'><div class='metric-label'>Score</div><div class='metric-value'>{row['score_geral']:.0f}</div></div>", unsafe_allow_html=True)
            
            st.info(row['justificativa'])
            
            # Botão do Link
            st.link_button("🔗 Ver Anúncio Original", row['link'], width="stretch")
            
            st.caption(f"ID: {row['id']} | Atualizado: {row['data_consulta']}")
        else:
            st.info("Ajuste os filtros para ver modelos.")

with tab2:
    st.header("Gestão de Anúncios")
    cols_gestao = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link']
    df_editor_db = st.data_editor(
        df_precos[cols_gestao],
        column_config={"ativo": st.column_config.CheckboxColumn("Ativo?"), "link": st.column_config.LinkColumn("Link")},
        hide_index=True, 
        disabled=["id", "data_consulta", "modelo", "link"], 
        key="editor_db"
        # use_container_width removido, padrão já é adequado ou use width="stretch" se necessário
    )
    if st.button("💾 Salvar DB"): salvar_alteracoes_db(df_editor_db)

with tab3:
    st.header("📚 Editor CSV (Régua Técnica)")
    # --- CORREÇÃO AQUI ---
    df_editor_csv = st.data_editor(df_ref_full, hide_index=True, width="stretch", key="editor_csv")
    
    if st.button("💾 Salvar CSV"):
        df_para_salvar = df_editor_csv.copy()
        if 'modelo_key' in df_para_salvar.columns: df_para_salvar.drop(columns=['modelo_key'], inplace=True)
        salvar_csv_editado(df_para_salvar)