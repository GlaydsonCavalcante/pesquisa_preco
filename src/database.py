import sqlite3
import os
from urllib.parse import urlparse, urlunparse

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
            termo_pesquisa TEXT,
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
    print("✅ Base de dados v3.1 (Com Verificação de Link) pronta.")

def limpar_link(url):
    """Remove parâmetros de rastreamento (?tracking_id=...) para evitar duplicatas reais."""
    try:
        if not url: return ""
        parsed = urlparse(url)
        # Reconstrói a URL sem 'query' (params) e sem 'fragment' (#)
        # Ex: produto.com?id=123&source=google -> produto.com
        # Nota: Alguns sites usam o ID na query, então vamos ser cuidadosos.
        # Para Mercado Livre, o ID está na URL path, então limpar query é seguro.
        if "mercadolivre" in url or "olx" in url:
            url_limpa = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        else:
            url_limpa = url # Outros sites podem precisar da query
        return url_limpa
    except:
        return url

def verificar_se_ja_existe(link_bruto):
    """Retorna True se este link já foi processado alguma vez na história."""
    if not link_bruto: return False
    
    link_limpo = limpar_link(link_bruto)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verifica se existe o link exato no banco
    # Dica: Se quiser reavaliar preços que mudaram, a lógica seria mais complexa.
    # Por enquanto, focamos em "não analisar o mesmo anúncio duas vezes".
    cursor.execute("SELECT id FROM precos WHERE link = ?", (link_limpo,))
    resultado = cursor.fetchone()
    conn.close()
    
    return resultado is not None

def salvar_no_banco(dados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    link_limpo = limpar_link(dados['link'])
    
    # Verificação dupla (para garantir que não salvamos duplicado no mesmo dia)
    cursor.execute(
        "SELECT id FROM precos WHERE link = ? AND data_consulta = ?", 
        (link_limpo, dados['data'])
    )
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
        dados['modelo'],
        dados.get('termo_usado', ''),
        dados['preco'],
        dados.get('custo_reparo', 0),
        dados['condicao'],
        dados.get('estado_detalhado', 'N/A'),
        dados['loja'], 
        dados['localizacao'], 
        1 if dados['tem_envio'] else 0, 
        link_limpo, 
        dados.get('ai_analise', ''),
        1
    ))
    
    conn.commit()
    conn.close()