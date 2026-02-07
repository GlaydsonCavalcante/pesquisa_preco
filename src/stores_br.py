import os
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote

def limpar_preco(texto):
    if not texto: return 0.0
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
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    
    # --- BLINDAGEM CONTRA ERRO DE CONEXÃO ---
    max_tentativas = 3
    for i in range(max_tentativas):
        try:
            servico = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=servico, options=chrome_options)
            return driver
        except Exception as e:
            print(f"⚠️ Erro ao iniciar driver (Tentativa {i+1}/{max_tentativas}): {e}")
            time.sleep(2)
            
    raise Exception("❌ Não foi possível iniciar o navegador após várias tentativas.")

def extrair_generico(soup, modelo_alvo, nome_loja):
    resultados = []
    termo_chave = modelo_alvo.lower().replace("roland", "").replace(" ", "").replace("-", "")
    
    links = soup.find_all('a', href=True)
    
    for link in links:
        try:
            texto_link = link.text.strip()
            if not texto_link: continue
            
            texto_comparacao = texto_link.lower().replace(" ", "").replace("-", "")
            
            if termo_chave in texto_comparacao:
                pai = link.parent
                container_produto = None
                
                for _ in range(3):
                    if pai:
                        if "R$" in pai.text:
                            container_produto = pai
                            break
                        pai = pai.parent
                
                if container_produto:
                    match_preco = re.search(r'R\$\s?[\d\.]+,?\d{0,2}', container_produto.text)
                    if match_preco:
                        preco_final = limpar_preco(match_preco.group(0))
                        if preco_final < 1500: continue
                        
                        href = link['href']
                        if not href.startswith('http'):
                            base_url = "https://www.teclacenter.com.br" if "teclacenter" in nome_loja.lower() else "https://www.ninjasom.com.br"
                            href = base_url + href

                        # Verifica duplicação local (na mesma execução)
                        if not any(r['link'] == href for r in resultados):
                            resultados.append({
                                'loja': nome_loja,
                                'modelo': modelo_alvo,
                                'titulo': texto_link,
                                'preco': preco_final,
                                'link': href,
                                'condicao': 'Novo',
                                'tem_envio': True,
                                'localizacao': 'Loja Online'
                            })
        except Exception:
            continue
    return resultados

def buscar_loja(driver, url_busca, modelo, nome_loja):
    print(f"--- Buscando na {nome_loja}... ---")
    try:
        driver.get(url_busca)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        itens = extrair_generico(soup, modelo, nome_loja)
        
        if not itens:
            modelo_simples = modelo.split()[-1]
            if len(modelo_simples) > 3:
                url_simples = url_busca.replace(quote(modelo), quote(modelo_simples))
                driver.get(url_simples)
                time.sleep(4)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                itens = extrair_generico(soup, modelo_simples, nome_loja)
            
        print(f"   Encontrados: {len(itens)}")
        return itens

    except Exception as e:
        print(f"Erro na {nome_loja}: {e}")
        return []

def executar_busca_lojas_br(modelo):
    try:
        driver = setup_driver()
    except Exception:
        print("⏩ Pulando Lojas BR devido a falha no driver.")
        return []

    todos_resultados = []
    try:
        url_tecla = f"https://www.teclacenter.com.br/catalogsearch/result/?q={quote(modelo)}"
        todos_resultados.extend(buscar_loja(driver, url_tecla, modelo, "TeclaCenter"))
        
        url_ninja = f"https://www.ninjasom.com.br/{quote(modelo)}"
        todos_resultados.extend(buscar_loja(driver, url_ninja, modelo, "Ninja Som"))
    finally:
        if driver: driver.quit()
        
    return todos_resultados