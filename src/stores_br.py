import os
from time import sleep
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote

def limpar_preco(texto):
    if not texto: return 0.0
    # Remove caracteres invisíveis e R$
    texto_limpo = re.sub(r'[^\d,]', '', texto)
    texto_limpo = texto_limpo.replace(',', '.')
    try:
        return float(texto_limpo)
    except:
        return 0.0

def setup_driver():
    caminho_projeto = os.getcwd()
    caminho_perfil = os.path.join(caminho_projeto, "chrome_perfil")
    
    chrome_options = Options()
    # Argumentos vitais para evitar crash
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_argument("--remote-debugging-port=9222") # <--- A CURA DO ERRO
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def extrair_generico(soup, modelo_alvo, nome_loja):
    """
    Tenta encontrar produtos numa página usando heurística visual:
    Procura blocos que contenham Título + Preço juntos.
    """
    resultados = []
    # Simplifica o modelo para busca no texto (ex: "Roland FP-30X" -> "fp30x")
    termo_chave = modelo_alvo.lower().replace("roland", "").replace(" ", "").replace("-", "")
    
    # 1. Encontrar todos os links da página
    # Geralmente o título do produto é um link
    links = soup.find_all('a', href=True)
    
    for link in links:
        try:
            texto_link = link.text.strip()
            if not texto_link: continue
            
            # Limpeza para comparação
            texto_comparacao = texto_link.lower().replace(" ", "").replace("-", "")
            
            # Verifica se o link tem o nome do modelo (ex: "fp30x")
            if termo_chave in texto_comparacao:
                # Achamos um candidato! Agora vamos procurar o preço PERTO dele.
                # Subimos para o elemento pai para procurar o preço no bloco
                pai = link.parent
                container_produto = None
                
                # Sobe até 3 níveis para achar o container do card
                for _ in range(3):
                    if pai:
                        if "R$" in pai.text:
                            container_produto = pai
                            break
                        pai = pai.parent
                
                if container_produto:
                    # Extrai o preço do texto completo do container
                    # Expressão regular para achar preços: R$ 1.234,56
                    match_preco = re.search(r'R\$\s?[\d\.]+,?\d{0,2}', container_produto.text)
                    
                    if match_preco:
                        preco_str = match_preco.group(0)
                        preco_final = limpar_preco(preco_str)
                        
                        # Filtro de sanidade (evitar cabos e acessórios)
                        if preco_final < 1500: continue
                        
                        # Evitar duplicatas pelo link
                        href = link['href']
                        if not href.startswith('http'):
                            # Corrige links relativos
                            base_url = "https://www.teclacenter.com.br" if "teclacenter" in nome_loja.lower() else "https://www.ninjasom.com.br"
                            href = base_url + href

                        # Verifica se já não adicionamos este item
                        ja_existe = any(r['link'] == href for r in resultados)
                        if not ja_existe:
                            resultados.append({
                                'loja': nome_loja,
                                'modelo': modelo_alvo,
                                'titulo': texto_link,
                                'preco': preco_final,
                                'link': href,
                                'condicao': 'Novo'
                            })
        except Exception:
            continue
            
    return resultados

def buscar_loja(driver, url_busca, modelo, nome_loja):
    print(f"--- Buscando na {nome_loja}... ---")
    try:
        driver.get(url_busca)
        sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Tenta extração genérica
        itens = extrair_generico(soup, modelo, nome_loja)
        
        if not itens:
            print(f"   (Tentativa 1 falhou. Tentando termo simplificado...)")
            # Tenta buscar só pelo modelo sem marca (ex: "FP-30X" em vez de "Roland FP-30X")
            modelo_simples = modelo.split()[-1] # Pega a última palavra
            url_simples = url_busca.replace(quote(modelo), quote(modelo_simples))
            driver.get(url_simples)
            sleep(4)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            itens = extrair_generico(soup, modelo_simples, nome_loja)
            
        print(f"   Encontrados: {len(itens)}")
        return itens

    except Exception as e:
        print(f"Erro na {nome_loja}: {e}")
        return []

def executar_busca_lojas_br(modelo):
    driver = setup_driver()
    todos_resultados = []
    
    try:
        # 1. TECLACENTER
        url_tecla = f"https://www.teclacenter.com.br/catalogsearch/result/?q={quote(modelo)}"
        res_tecla = buscar_loja(driver, url_tecla, modelo, "TeclaCenter")
        todos_resultados.extend(res_tecla)
        
        # 2. NINJA SOM
        # Ninja Som usa VTEX, busca geralmente é /busca?ft=
        url_ninja = f"https://www.ninjasom.com.br/{quote(modelo)}" # Tentativa url direta
        res_ninja = buscar_loja(driver, url_ninja, modelo, "Ninja Som")
        todos_resultados.extend(res_ninja)
        
    finally:
        driver.quit()
        
    return todos_resultados

if __name__ == "__main__":
    # Teste
    modelo = "Roland FP-30X"
    print(f"🔎 Iniciando busca BR para: {modelo}")
    
    resultados = executar_busca_lojas_br(modelo)
    
    print("\n--- RESUMO LOJAS BRASIL ---")
    if resultados:
        for item in resultados:
            print(f"🏢 {item['loja']}")
            print(f"🎹 {item['titulo']}")
            print(f"💰 R$ {item['preco']:,.2f}")
            print(f"🔗 {item['link']}")
            print("-" * 30)
    else:
        print("Nenhum produto novo encontrado (verifique se o site não mudou ou bloqueou).")