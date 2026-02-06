import sqlite3
import os

# Caminho para o banco de dados
DB_PATH = os.path.join("data", "historico_precos.db")

def criar_tabela():
    """
    Cria a tabela no banco de dados SQLite se ela não existir.
    """
    # Garante que a pasta 'data' existe
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Pasta 'data' criada.")

    # Conecta ao banco (cria o arquivo se não existir)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Criação da tabela com colunas para Logística e Preço
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_consulta TEXT,
            modelo TEXT,
            preco REAL,
            condicao TEXT,       -- Novo ou Usado
            loja TEXT,           -- Ex: Mercado Livre, OLX
            localizacao TEXT,    -- Ex: Brasília, DF, ou Outro
            tem_envio INTEGER,   -- 1 para Sim, 0 para Não
            link TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Base de dados verificada/criada com sucesso em: {DB_PATH}")

# Este bloco permite testar o arquivo rodando-o diretamente
if __name__ == "__main__":
    criar_tabela()