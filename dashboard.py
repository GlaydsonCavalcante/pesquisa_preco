import streamlit as st
import pandas as pd
import plotly.express as px
import time
import sys
import os

# Importa os serviços da pasta src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
import dashboard_services as service

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Piano Scout Manager", layout="wide")

st.markdown("""
<style>
    /* Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0 0; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #4CAF50; }
    
    /* Métricas Compactas */
    .metric-compact {
        background: #f8f9fa; padding: 5px; border-radius: 4px; 
        text-align: center; border: 1px solid #eee;
    }
    .metric-compact label { font-size: 9px; text-transform: uppercase; color: #666; display: block; }
    .metric-compact value { font-size: 14px; font-weight: bold; color: #333; }
    
    /* Badges */
    .status-badge {
        padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white;
    }
    
    /* Empty State */
    .empty-state {
        text-align: center; padding: 40px 10px; color: #bbb;
        border: 2px dashed #eee; border-radius: 8px; margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO ---
service.init_config_db()

def save_config_callback():
    service.update_dashboard_config(
        st.session_state.n_min_score, st.session_state.n_max_score,
        st.session_state.n_min_preco, st.session_state.n_max_preco
    )

df_raw, df_full = service.carregar_dados_completos()

if df_full is None or df_full.empty:
    st.error("⚠️ Sem dados. Execute main.py.")
    st.stop()

df_ativos = df_full[df_full['ativo'] == True].copy()
stats_mercado = service.calcular_estatisticas_mercado(df_ativos)

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📊 Matriz de Decisão", "📝 Gestão de Anúncios", "📚 Editor AHSD (CSV)"])

with tab1:
    # Filtros
    cfg = service.get_dashboard_config()
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.number_input("Min Score", 0, 100, cfg['min_score'], key='n_min_score', on_change=save_config_callback)
    with c2: st.number_input("Max Score", 0, 100, cfg['max_score'], key='n_max_score', on_change=save_config_callback)
    with c3: st.number_input("Min Preço", 0.0, step=100.0, value=float(cfg['min_preco']), key='n_min_preco', on_change=save_config_callback)
    with c4: st.number_input("Max Preço", 0.0, step=100.0, value=float(cfg['max_preco']), key='n_max_preco', on_change=save_config_callback)

    # Filtragem dos dados
    df_plot = df_ativos[
        (df_ativos['score_geral'] >= st.session_state.n_min_score) & 
        (df_ativos['score_geral'] <= st.session_state.n_max_score) &
        (df_ativos['custo_total'] >= st.session_state.n_min_preco) &
        (df_ativos['custo_total'] <= st.session_state.n_max_preco)
    ].copy()

    col_grafico, col_detalhes = st.columns([3, 1])

    with col_grafico:
        if not df_plot.empty:
            idx_melhores = df_plot.groupby('modelo_key')['custo_total'].idxmin()
            df_chart = df_plot.loc[idx_melhores].reset_index(drop=True)
            
            # Legenda e Cores das Bolhas
            df_chart['legenda'] = df_chart.apply(
                lambda x: '⭐ PRIORIDADE' if str(x.get('priorizado', False)).lower() in ['true', 'sim'] else x['condicao'], axis=1
            )
            
            # Limites e Pontos Médios para os Quadrantes
            min_s, max_s = df_chart['score_geral'].min(), df_chart['score_geral'].max()
            min_p, max_p = df_chart['custo_total'].min(), df_chart['custo_total'].max()
            
            # Ajuste de margem para não cortar as bolhas
            margem_x = 5 if min_s == max_s else (max_s - min_s) * 0.1
            margem_y = 500 if min_p == max_p else (max_p - min_p) * 0.1
            
            # Definição dos eixos reais do gráfico
            x_start, x_end = min_s - margem_x, max_s + margem_x
            y_start, y_end = min_p - margem_y, max_p + margem_y
            
            mid_x = (x_end + x_start) / 2
            mid_y = (y_end + y_start) / 2

            fig = px.scatter(
                df_chart, x="score_geral", y="custo_total", color="legenda",
                color_discrete_map={"⭐ PRIORIDADE": "#FFD700", "Novo": "#2E86C1", "Usado": "#28B463"},
                text="modelo", # Nome acima da bolha
                hover_name="modelo",
                custom_data=['modelo_key', 'id'],
                height=650, title="<b>Matriz Qualidade vs Preço</b>"
            )

            # CONFIGURAÇÃO: Bolhas tamanho 12 e Texto Acima
            fig.update_traces(
                textposition='top center',
                marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey'))
            )

            # QUADRANTES (Pintar o fundo)
            # Verde (Baixo Direito): Score Alto, Preço Baixo
            fig.add_shape(type="rect", x0=mid_x, x1=x_end, y0=y_start, y1=mid_y, 
                         fillcolor="rgba(46, 204, 113, 0.15)", layer="below", line_width=0)
            # Azul (Alto Direito): Score Alto, Preço Alto
            fig.add_shape(type="rect", x0=mid_x, x1=x_end, y0=mid_y, y1=y_end, 
                         fillcolor="rgba(52, 152, 219, 0.15)", layer="below", line_width=0)
            # Laranja (Baixo Esquerdo): Score Baixo, Preço Baixo
            fig.add_shape(type="rect", x0=x_start, x1=mid_x, y0=y_start, y1=mid_y, 
                         fillcolor="rgba(241, 196, 15, 0.15)", layer="below", line_width=0)
            # Vermelho (Alto Esquerdo): Score Baixo, Preço Alto
            fig.add_shape(type="rect", x0=x_start, x1=mid_x, y0=mid_y, y1=y_end, 
                         fillcolor="rgba(231, 76, 60, 0.15)", layer="below", line_width=0)
            
            # Anotações dos Quadrantes
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
            
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")
        else:
            st.info("Ajuste os filtros.")
            event = None

    with col_detalhes:
        selected_key = None
        if event and event['selection']['points']:
            selected_key = event['selection']['points'][0]['customdata'][0]
        
        if selected_key:
            item = df_chart[df_chart['modelo_key'] == selected_key].iloc[0]
            stats = stats_mercado[stats_mercado['modelo_key'] == selected_key].iloc[0]
            
            # Cabeçalho Compacto
            st.markdown(f"**{item['modelo']}**")
            
            estado = str(item.get('estado_detalhado', 'N/A')).replace('_', ' ').title()
            cor = "#27AE60" if "novo" in estado.lower() or "otimo" in estado.lower() else "#F39C12"
            st.markdown(f"<span class='status-badge' style='background-color:{cor}'>{estado}</span>", unsafe_allow_html=True)
            
            # Preço Grande
            st.markdown(f"<h2 style='color:#2E86C1; margin:5px 0'>R$ {item['custo_total']:,.0f}</h2>", unsafe_allow_html=True)
            
            # Stats Mercado (Compacto)
            c_m1, c_m2 = st.columns(2)
            c_m1.markdown(f"<div class='metric-compact'><label>Máximo</label><value>R$ {stats['Maximo']:,.0f}</value></div>", unsafe_allow_html=True)
            pct = ((item['custo_total']/stats['MediaGeo'])-1)*100
            cor_pct = "red" if pct > 0 else "green"
            c_m2.markdown(f"<div class='metric-compact'><label>vs Média</label><value style='color:{cor_pct}'>{pct:+.1f}%</value></div>", unsafe_allow_html=True)
            
            st.write("") # Espaçamento mínimo
            
            # Score Técnico (Compacto)
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-compact'><label>Mec</label><value>{item['mecanica']}</value></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-compact'><label>Som</label><value>{item['som_polifonia']}</value></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-compact'><label>Geral</label><value>{item['score_geral']:.0f}</value></div>", unsafe_allow_html=True)
            
            if item.get('justificativa'):
                with st.expander("Justificativa IA", expanded=False):
                    st.caption(item['justificativa'])
            
            st.write("")
            
            # Botões
            st.link_button("🔗 Ver Anúncio", item['link'], use_container_width=True)
            if st.button("🗑️ Desativar", key="btn_del", type="secondary", use_container_width=True):
                service.atualizar_status_item(item['id'], False)
                st.toast("Removido!", icon="✅")
                time.sleep(0.5)
                st.rerun()
                
        else:
            st.markdown("<div class='empty-state'>👆 Selecione um item<br>para ver detalhes</div>", unsafe_allow_html=True)

with tab2:
    st.header("Gestão de Dados")
    cols = ['id', 'ativo', 'data_consulta', 'modelo', 'preco', 'custo_reparo', 'estado_detalhado', 'link']
    df_ed = st.data_editor(df_raw[cols], column_config={"link": st.column_config.LinkColumn()}, hide_index=True, disabled=["id", "modelo"], height=600)
    if st.button("💾 Salvar"):
        service.salvar_lote_db(df_ed)
        st.success("Salvo!")
        time.sleep(1)
        st.rerun()

with tab3:
    st.header("Editor CSV")
    try: df_csv = pd.read_csv(service.CSV_PATH, on_bad_lines='skip')
    except: df_csv = pd.DataFrame()
    df_csv_ed = st.data_editor(df_csv, hide_index=True, num_rows="dynamic")
    if st.button("💾 Salvar CSV"):
        service.salvar_csv(df_csv_ed)
        st.success("CSV Salvo!")