import sqlite3
import os

DB_PATH = os.path.join("data", "historico_precos.db")

def criar_tabela():
    if not os.path.exists("data"):
        os.makedirs("data")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Novas colunas:
    # estado_detalhado: novo, otimo, funcional, etc.
    # custo_reparo: valor estimado pela IA
    # ativo: 1 (Sim) ou 0 (Não) - Para "soft delete"
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_consulta TEXT,
            modelo TEXT,
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
    print("✅ Base de dados v2.0 criada.")

def salvar_no_banco(dados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Evita duplicatas no mesmo dia
    cursor.execute("SELECT id FROM precos WHERE link = ? AND data_consulta = ?", (dados['link'], dados['data']))
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute('''
        INSERT INTO precos (
            data_consulta, modelo, preco, custo_reparo, condicao, 
            estado_detalhado, loja, localizacao, tem_envio, link, ai_analise, ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dados['data'], 
        dados['modelo'], 
        dados['preco'],
        dados.get('custo_reparo', 0),
        dados['condicao'],
        dados.get('estado_detalhado', 'N/A'),
        dados['loja'], 
        dados['localizacao'], 
        1 if dados['tem_envio'] else 0, 
        dados['link'],
        dados.get('ai_analise', ''),
        1 # Ativo por padrão
    ))
    
    conn.commit()
    conn.close()

def carregar_tudo_para_edicao():
    """Função para o Dashboard de Gestão"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM precos", conn)
    conn.close()
    return df

def atualizar_status_ativo(id_produto, novo_status):
    """Permite inativar um anúncio pelo Dashboard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE precos SET ativo = ? WHERE id = ?", (novo_status, id_produto))
    conn.commit()
    conn.close()