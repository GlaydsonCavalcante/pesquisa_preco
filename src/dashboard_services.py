import sqlite3
import pandas as pd
import numpy as np
import os

# Caminhos
DB_PATH = os.path.join("data", "historico_precos.db")
CSV_PATH = os.path.join("data", "modelos_alvo.csv")

# --- BANCO DE DADOS & CONFIGURAÇÃO ---
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

def update_dashboard_config(min_s, max_s, min_p, max_p):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE config_dashboard 
        SET min_score = ?, max_score = ?, min_preco = ?, max_preco = ? 
        WHERE id = 1
    """, (min_s, max_s, min_p, max_p))
    conn.commit()
    conn.close()

# --- DADOS ---
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