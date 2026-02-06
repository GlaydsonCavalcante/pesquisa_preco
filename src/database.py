import sqlite3
import os

DB_PATH = os.path.join("data", "historico_precos.db")

def criar_tabela():
    if not os.path.exists("data"):
        os.makedirs("data")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_consulta TEXT,
            modelo TEXT,
            preco REAL,
            condicao TEXT,
            loja TEXT,
            localizacao TEXT,
            tem_envio INTEGER,
            link TEXT,
            ai_analise TEXT  -- Nova coluna para guardar o que a IA pensou
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Base de dados (re)criada com estrutura para IA.")

def salvar_no_banco(dados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verifica se esse link JÁ foi salvo hoje para evitar duplicata no mesmo dia
    cursor.execute("SELECT id FROM precos WHERE link = ? AND data_consulta = ?", (dados['link'], dados['data']))
    if cursor.fetchone():
        conn.close()
        return # Já salvamos hoje, ignora.

    cursor.execute('''
        INSERT INTO precos (data_consulta, modelo, preco, condicao, loja, localizacao, tem_envio, link, ai_analise)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dados['data'], 
        dados['modelo'], 
        dados['preco'], 
        dados['condicao'], 
        dados['loja'], 
        dados['localizacao'], 
        1 if dados['tem_envio'] else 0, 
        dados['link'],
        dados.get('ai_analise', '')
    ))
    
    conn.commit()
    conn.close()