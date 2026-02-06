import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# Configuração da Página
st.set_page_config(page_title="Piano Scout Analytics", layout="wide")

st.title("🎹 Piano Scout: Cockpit de Inteligência")
st.markdown("""
<style>
    .big-font { font-size:20px !important; }
    .justificativa { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

def carregar_dados_completos():
    if not os.path.exists(DB_PATH): return None, None
    conn = sqlite3.connect(DB_PATH)
    df_precos = pd.read_sql_query("SELECT * FROM precos", conn)
    conn.close()

    if not os.path.exists(CSV_PATH): return None, None
    df_ref = pd.read_csv(CSV_PATH)

    df_full = pd.merge(df_precos, df_ref, on='modelo', how='left')
    df_full['data_consulta'] = pd.to_datetime(df_full['data_consulta'])
    
    return df_full, df_ref

def calcular_estatisticas(df_modelo):
    if df_modelo.empty: return None
    stats = {
        'min': df_modelo['preco'].min(),
        'mediana': df_modelo['preco'].median(),
        'max': df_modelo['preco'].max(),
        'qtd': len(df_modelo)
    }
    return stats

# --- LÓGICA DO DASHBOARD ---
df_full, df_ref = carregar_dados_completos()

if df_full is not None and not df_full.empty:
    
    data_recente = df_full['data_consulta'].max().strftime('%Y-%m-%d')
    st.info(f"📅 Visualizando dados consolidados até: **{data_recente}**")

    st.subheader("📈 Matriz de Valor: Qualidade vs. Preço")
    
    df_grafico = df_full[df_full['data_consulta'] == df_full['data_consulta'].max()].copy()
    
    # Prepara tamanho da bolha
    # Adiciona um pequeno valor para evitar divisão por zero se preço for zero
    df_grafico['tamanho_bolha'] = (1 / (df_grafico['preco'] + 1 / df_grafico['score_geral'])) * 100000

    # --- CORREÇÃO AQUI: REMOVIDO 'TITULO' DO HOVER_DATA ---
    fig = px.scatter(
        df_grafico,
        x="score_geral",
        y="preco",
        color="condicao",
        size="tamanho_bolha",
        hover_name="modelo",
        hover_data={
            "loja": True,
            "link": False,
            "tamanho_bolha": False,
            "score_geral": True,
            "preco": ":.2f"
        },
        text="modelo",
        title="Dispersão de Oportunidades",
        labels={"score_geral": "Score (Qualidade)", "preco": "Preço (R$)", "condicao": "Condição"},
        height=600
    )
    
    fig.update_traces(textposition='top center')
    fig.update_layout(
        xaxis=dict(range=[60, 100]), 
        yaxis=dict(autorange="reversed"), 
        legend_title="Estado"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📋 Análise Detalhada por Modelo")

    for index, row in df_ref.iterrows():
        modelo = row['modelo']
        score = row['score_geral']
        
        dados_modelo = df_full[df_full['modelo'] == modelo]
        
        with st.expander(f"🎹 {modelo} (Score: {score})", expanded=False):
            st.markdown(f"""
            <div class="justificativa">
                <b>💡 Avaliação:</b> {row['justificativa']}<br>
                Mecânica: {row['mecanica']} | Som: {row['som_polifonia']}
            </div>
            """, unsafe_allow_html=True)
            st.write("")

            novos = dados_modelo[dados_modelo['condicao'] == 'Novo']
            usados = dados_modelo[dados_modelo['condicao'] == 'Usado']
            
            stats_novos = calcular_estatisticas(novos)
            stats_usados = calcular_estatisticas(usados)

            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 🆕 Novo (Referência)")
                if stats_novos:
                    st.metric("Mínimo", f"R$ {stats_novos['min']:,.2f}")
                    st.caption(f"Mediana: R$ {stats_novos['mediana']:,.2f}")
                    # Tenta pegar a loja de referência
                    if 'loja' in novos.columns:
                        loja = novos.iloc[0]['loja']
                        st.write(f"🏠 {loja}")
                else:
                    st.warning("Sem dados.")

            with col2:
                st.markdown("### 📦 Usado")
                if stats_usados:
                    delta = 0
                    if stats_novos:
                        delta = -((stats_novos['min'] - stats_usados['min']) / stats_novos['min']) * 100
                    
                    st.metric("Melhor Preço", f"R$ {stats_usados['min']:,.2f}", delta=f"{delta:.1f}% vs Novo")
                    st.caption(f"Mediana: R$ {stats_usados['mediana']:,.2f}")
                else:
                    st.warning("Sem dados.")

            with col3:
                st.markdown("### 🔗 Links")
                if not usados.empty:
                    top_usados = usados.sort_values('preco').head(3)
                    for i, item in top_usados.iterrows():
                        # Verifica se 'localizacao' existe no dataframe antes de acessar
                        local = item['localizacao'] if 'localizacao' in item else "N/A"
                        
                        st.markdown(f"""
                        **R$ {item['preco']:,.2f}** [Ver Anúncio]({item['link']}) | 📍 {local}
                        """, unsafe_allow_html=True)
                        st.divider()

else:
    st.error("Execute 'python main.py' para popular o banco de dados.")