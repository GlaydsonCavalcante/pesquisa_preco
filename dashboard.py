import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import numpy as np
import time
import sys

# Adiciona pasta src ao path se necessário
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Tenta importar serviços, se falhar define localmente (fallback)
try:
    import dashboard_services as service
except ImportError:
    pass

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Piano Scout Manager", layout="wide")

# CSS Personalizado
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #4CAF50; }
    
    .metric-box {
        text-align: center; background: white; padding: 10px;
        border-radius: 8px; border: 1px solid #eee; margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 16px; font-weight: 700; color: #333; }
    
    .status-badge {
        display: inline-block; padding: 4px 10px; border-radius: 12px;
        font-size: 12px; font-weight: bold; color: white; margin-bottom: 10px;
    }
    
    .empty-state {
        text-align: center; padding: 40px 10px; color: #bbb;
        border: 2px dashed #eee; border-radius: 8px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

# --- FUNÇÕES DE SUPORTE LOCAIS (Caso dashboard_services falhe ou para simplificar) ---
def init_config_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_dashboard (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            min_score INTEGER DEFAULT 50,
            max_score INTEGER DEFAULT 100,
            min_preco REAL DEFAULT 1500.0,
            max_preco REAL DEFAULT 50000.0
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO config_dashboard (id, min_score, max_score, min_preco, max_preco) VALUES (1, 50, 100, 1500.0, 50000.0)")
    conn.commit()
    conn.close()

def get_dashboard_config():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT min_score, max_score, min_preco, max_preco FROM config_dashboard WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"min_score": row[0], "max_score": row[1], "min_preco": row[2], "max_preco": row[3]}
    return {"min_score": 50, "max_score": 100, "min_preco": 1500.0, "max_preco": 50000.0}

def save_config_callback():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE config_dashboard 
        SET min_score = ?, max_score = ?, min_preco = ?, max_preco = ? 
        WHERE id = 1
    """, (
        st.session_state.n_min_score,
        st.session_state.n_max_score,
        st.session_state.n_min_preco,
        st.session_state.n_max_preco
    ))
    conn.commit()
    conn.close()

def carregar_dados_completos():
    if not os.path.exists(DB_PATH): return None, None
    conn = sqlite3.connect(DB_PATH)
    df_precos = pd.read_sql_query("SELECT * FROM precos", conn)
    conn.close()

    try:
        df_ref = pd.read_csv(CSV_PATH, on_bad_lines='skip')
    except:
        df_ref = pd.DataFrame()

    if not df_precos.empty and not df_ref.empty:
        df_precos['modelo_key'] = df_precos['modelo'].astype(str).str.strip().str.upper()
        df_ref['modelo_key'] = df_ref['modelo'].astype(str).str.strip().str.upper()
        
        df_full = pd.merge(df_precos, df_ref, on='modelo_key', how='left', suffixes=('', '_csv'))
        df_full['custo_reparo'] = df_full['custo_reparo'].fillna(0)
        df_full['custo_total'] = df_full['preco'] + df_full['custo_reparo']
        df_full['ativo'] = df_full['ativo'].apply(lambda x: x in [1, '1', True, 'True'])
        return df_precos, df_full
    return df_precos, pd.DataFrame()

def atualizar_status_item(id_anuncio, ativo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (1 if ativo else 0, int(id_anuncio)))
    conn.commit()
    conn.close()

def salvar_lote_db(df_editado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for _, row in df_editado.iterrows():
        cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (1 if row['ativo'] else 0, row['id']))
    conn.commit()
    conn.close()

def salvar_csv(df):
    df.to_csv(CSV_PATH, index=False)

def media_geometrica(series):
    arr = np.array(series)
    arr = arr[arr > 0]
    if len(arr) == 0: return 0
    return np.exp(np.mean(np.log(arr)))

def calcular_estatisticas_mercado(df_ativos):
    return df_ativos.groupby('modelo_key')['custo_total'].agg(
        Minimo='min', Maximo='max', MediaGeo=media_geometrica, Qtd='count'
    ).reset_index()

# --- INICIALIZAÇÃO DO APP ---
init_config_db()
df_raw, df_full = carregar_dados_completos()

if df_full is None or df_full.empty:
    st.error("⚠️ Sem dados. Execute main.py.")
    st.stop()

df_ativos = df_full[df_full['ativo'] == True].copy()
stats_mercado = calcular_estatisticas_mercado(df_ativos)

# --- LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📊 Matriz de Decisão", "📝 Gestão de Anúncios", "📚 Editor AHSD (CSV)"])

with tab1:
    # --- FILTROS ---
    cfg = get_dashboard_config()
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.number_input("Min Score", 0, 100, cfg['min_score'], key='n_min_score', on_change=save_config_callback)
    with c2: st.number_input("Max Score", 0, 100, cfg['max_score'], key='n_max_score', on_change=save_config_callback)
    with c3: st.number_input("Min Preço", 0.0, step=100.0, value=float(cfg['min_preco']), key='n_min_preco', on_change=save_config_callback)
    with c4: st.number_input("Max Preço", 0.0, step=100.0, value=float(cfg['max_preco']), key='n_max_preco', on_change=save_config_callback)

    # --- DEFINIÇÃO DO DATAFRAME FILTRADO (Correção do NameError) ---
    df_plot_filtered = df_ativos[
        (df_ativos['score_geral'] >= st.session_state.n_min_score) & 
        (df_ativos['score_geral'] <= st.session_state.n_max_score) &
        (df_ativos['custo_total'] >= st.session_state.n_min_preco) &
        (df_ativos['custo_total'] <= st.session_state.n_max_preco)
    ].copy()

    col_grafico, col_detalhes = st.columns([3, 1])

    with col_grafico:
        if not df_plot_filtered.empty:
            # Agrupa pelo menor preço para plotar, mas mantém o ID para referência
            idx_melhores = df_plot_filtered.groupby('modelo_key')['custo_total'].idxmin()
            df_plot = df_plot_filtered.loc[idx_melhores].copy().reset_index(drop=True)

            # --- MAPA DE CORES ---
            MAPA_CORES = {
                "⭐ PRIORIDADE": "#FFD700",
                "Novo": "#2980B9",
                "Ótimo Estado": "#27AE60",
                "Funcional": "#F39C12",
                "Semifuncional": "#D35400",
                "Não Funcional": "#C0392B"
            }

            def obter_legenda_detalhada(row):
                if str(row.get('priorizado', False)).lower() in ['true', 'sim']: return "⭐ PRIORIDADE"
                estado_bd = str(row.get('estado_detalhado', '')).lower()
                if 'novo' in estado_bd: return "Novo"
                if 'otimo' in estado_bd or 'ótimo' in estado_bd: return "Ótimo Estado"
                if 'semi' in estado_bd: return "Semifuncional"
                if 'nao' in estado_bd or 'não' in estado_bd: return "Não Funcional"
                return "Funcional"

            df_plot['legenda'] = df_plot.apply(obter_legenda_detalhada, axis=1)

            # Limites e Layout
            min_s, max_s = df_plot['score_geral'].min(), df_plot['score_geral'].max()
            min_p, max_p = df_plot['custo_total'].min(), df_plot['custo_total'].max()
            margem_x = 5 if min_s == max_s else (max_s - min_s) * 0.15
            margem_y = 500 if min_p == max_p else (max_p - min_p) * 0.15
            x_start, x_end = min_s - margem_x, max_s + margem_x
            y_start, y_end = min_p - margem_y, max_p + margem_y
            mid_x = (x_end + x_start) / 2
            mid_y = (y_end + y_start) / 2
            
            # Gráfico Principal
            fig = px.scatter(
                df_plot, x="score_geral", y="custo_total", color="legenda",
                color_discrete_map=MAPA_CORES,
                text="modelo", hover_name="modelo",
                custom_data=['id', 'modelo_key'], # ID é o primeiro dado customizado
                height=700, labels={"score_geral": "Qualidade", "custo_total": "Preço"}
            )
            
            fig.update_traces(textposition='top center', marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
            
            # Quadrantes
            fig.add_shape(type="rect", x0=mid_x, x1=x_end, y0=y_start, y1=mid_y, fillcolor="rgba(46, 204, 113, 0.15)", layer="below", line_width=0)
            fig.add_shape(type="rect", x0=mid_x, x1=x_end, y0=mid_y, y1=y_end, fillcolor="rgba(52, 152, 219, 0.15)", layer="below", line_width=0)
            fig.add_shape(type="rect", x0=x_start, x1=mid_x, y0=y_start, y1=mid_y, fillcolor="rgba(241, 196, 15, 0.15)", layer="below", line_width=0)
            fig.add_shape(type="rect", x0=x_start, x1=mid_x, y0=mid_y, y1=y_end, fillcolor="rgba(231, 76, 60, 0.15)", layer="below", line_width=0)
            
            # Anotações
            fig.add_annotation(x=x_end, y=y_start, text="OPORTUNIDADE", showarrow=False, xanchor="right", yanchor="bottom", font=dict(color="green", size=10))
            fig.add_annotation(x=x_end, y=y_end, text="PREMIUM", showarrow=False, xanchor="right", yanchor="top", font=dict(color="blue", size=10))
            fig.add_annotation(x=x_start, y=y_start, text="ENTRADA", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color="orange", size=10))
            fig.add_annotation(x=x_start, y=y_end, text="EVITAR", showarrow=False, xanchor="left", yanchor="top", font=dict(color="red", size=10))

            fig.update_layout(
                xaxis=dict(range=[x_start, x_end], title="Qualidade (Score)", showgrid=False),
                yaxis=dict(range=[y_start, y_end], title="Preço (R$)", showgrid=False),
                clickmode='event+select',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            # Correção de Depreciação: width='stretch' em vez de use_container_width=True
            event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points")
        else:
            st.warning("Nenhum modelo encontrado com estes filtros.")
            event = None

    with col_detalhes:
        row = None
        
        # 1. Tenta pegar pelo clique (ID específico)
        if event and event.get('selection') and event['selection']['points']:
            selected_id = event['selection']['points'][0]['customdata'][0]
            # Busca no dataframe original de ativos para garantir consistência
            row_search = df_ativos[df_ativos['id'] == selected_id]
            if not row_search.empty:
                row = row_search.iloc[0]
        
        # 2. Fallback: Se não clicou, pega o destaque do gráfico (o melhor custo-benefício visível)
        elif not df_plot_filtered.empty and 'df_plot' in locals():
            # (O df_plot já contém os melhores de cada modelo visível)
            row = df_plot.loc[df_plot['score_geral'].idxmax()]
        
        if row is not None:
            stats = stats_mercado[stats_mercado['modelo_key'] == row['modelo_key']].iloc[0]
            
            st.markdown(f"### {row['modelo']}")
            st.caption(f"🆔 ID: {row['id']}") # Útil para auditoria
            
            estado_raw = str(row.get('estado_detalhado', 'funcional')).replace('_', ' ').title()
            cor_estado = "#27AE60" if "Novo" in estado_raw else "#F39C12"
            if "Semi" in estado_raw: cor_estado = "#D35400"
            st.markdown(f"<span class='status-badge' style='background-color:{cor_estado}'>{estado_raw}</span>", unsafe_allow_html=True)
            
            st.markdown(f"<h2 style='color:#2E86C1; margin:5px 0'>R$ {row['custo_total']:,.0f}</h2>", unsafe_allow_html=True)
            
            c_m1, c_m2 = st.columns(2)
            c_m1.markdown(f"<div class='metric-compact'><label>Máximo</label><value>R$ {stats['Maximo']:,.0f}</value></div>", unsafe_allow_html=True)
            pct = ((row['custo_total']/stats['MediaGeo'])-1)*100
            cor_pct = "red" if pct > 0 else "green"
            c_m2.markdown(f"<div class='metric-compact'><label>vs Média</label><value style='color:{cor_pct}'>{pct:+.1f}%</value></div>", unsafe_allow_html=True)
            
            st.write("")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-compact'><label>Mec</label><value>{row['mecanica']}</value></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-compact'><label>Som</label><value>{row['som_polifonia']}</value></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-compact'><label>Geral</label><value>{row['score_geral']:.0f}</value></div>", unsafe_allow_html=True)
            
            if row.get('ai_analise'):
                with st.expander("🤖 Análise IA", expanded=False):
                    st.caption(row['ai_analise'])
            
            st.write("")
            
            st.link_button("🔗 Ver Anúncio Real", row['link'], use_container_width=True)
            
            if st.button("❌ Desativar (Erro/Lixo)", key=f"btn_del_{row['id']}", type="primary", use_container_width=True):
                atualizar_status_item(row['id'], False)
                st.toast(f"ID {row['id']} removido!", icon="🗑️")
                time.sleep(0.5)
                st.rerun()

        else:
            st.markdown("<div class='empty-state'>👆 Selecione um item<br>para ver detalhes</div>", unsafe_allow_html=True)

with tab2:
    st.header("Gestão de Dados")
    cols = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link']
    df_ed = st.data_editor(df_raw[cols], column_config={"link": st.column_config.LinkColumn()}, hide_index=True, disabled=["id", "modelo"], height=600)
    if st.button("💾 Salvar Banco"):
        salvar_lote_db(df_ed)
        st.success("Salvo!")
        time.sleep(1)
        st.rerun()

with tab3:
    st.header("Editor CSV")
    try: df_csv = pd.read_csv(CSV_PATH, on_bad_lines='skip')
    except: df_csv = pd.DataFrame()
    df_csv_ed = st.data_editor(df_csv, hide_index=True, num_rows="dynamic")
    if st.button("💾 Salvar CSV"):
        salvar_csv(df_csv_ed)
        st.success("CSV Salvo!")