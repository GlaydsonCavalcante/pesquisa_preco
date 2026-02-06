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
            modelo TEXT,           -- Nome Oficial do CSV (para o gráfico funcionar)
            termo_pesquisa TEXT,   -- O que digitamos na busca (ex: "FP-30X")
            preco REAL,
            custo_reparo REAL DEFAULT 0,
            condicao TEXT,
            estado_detalhado TEXT, 
            loja TEXT,
            localizacao TEXT,
            tem_envio INTEGER,
            link TEXT,
            ai_analise TEXT,
            ativo INTEGER DEFAULT 1
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Base de dados v3.0 (Relacional) criada.")

def salvar_no_banco(dados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Evita duplicatas
    cursor.execute("SELECT id FROM precos WHERE link = ? AND data_consulta = ?", (dados['link'], dados['data']))
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute('''
        INSERT INTO precos (
            data_consulta, modelo, termo_pesquisa, preco, custo_reparo, condicao, 
            estado_detalhado, loja, localizacao, tem_envio, link, ai_analise, ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dados['data'], 
        dados['modelo'],             # Sempre o nome do CSV
        dados.get('termo_usado', ''), # O termo que usamos na busca
        dados['preco'],
        dados.get('custo_reparo', 0),
        dados['condicao'],
        dados.get('estado_detalhado', 'N/A'),
        dados['loja'], 
        dados['localizacao'], 
        1 if dados['tem_envio'] else 0, 
        dados['link'],
        dados.get('ai_analise', ''),
        1
    ))
    
    conn.commit()
    conn.close()