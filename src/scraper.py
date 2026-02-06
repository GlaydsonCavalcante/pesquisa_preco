import os
from time import sleep
import random # Importante para variar o tempo
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def limpar_preco(texto):
    if not texto: return 0.0
    apenas_numeros = re.sub(r'[^\d,]', '', texto)
    apenas_numeros = apenas_numeros.replace(',', '.')
    try:
        return float(apenas_numeros)
    except:
        return 0.0

def buscar_mercadolivre(modelo):
    print(f"--- 🕵️ CAÇADOR INICIADO: {modelo} ---")
    
    # Cria o caminho absoluto para a pasta de perfil dentro do projeto
    caminho_projeto = os.getcwd()
    caminho_perfil = os.path.join(caminho_projeto, "chrome_perfil")
    
    chrome_options = Options()
    # chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_argument("--log-level=3")
    
    # --- NOVIDADE: PERSISTÊNCIA DE DADOS ---
    # Isso cria uma pasta 'chrome_perfil' e salva cookies/cache lá.
    chrome_options.add_argument(f"user-data-dir={caminho_perfil}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    resultados = []

    try:
        url = f"https://lista.mercadolivre.com.br/{modelo.replace(' ', '-')}"
        # print(f"Acessando: {url}") # Menos verboso
        driver.get(url)
        
        # --- DICA DE SEGURANÇA ---
        # Aumentamos o tempo de espera aleatório para parecer mais humano
        tempo_espera = random.uniform(4, 7) 
        sleep(tempo_espera)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        produtos_html = soup.find_all('li', class_='ui-search-layout__item')
        if not produtos_html:
            produtos_html = soup.find_all('div', class_='ui-search-result__wrapper')
        if not produtos_html:
            produtos_html = soup.find_all('div', class_='andes-card')
            
        # print(f"Itens detectados: {len(produtos_html)}")

        for produto in produtos_html:
            try:
                # TÍTULO
                titulo_elem = produto.find('h2', class_='ui-search-item__title')
                if not titulo_elem: titulo_elem = produto.find('a', class_='ui-search-item__group__element')
                if not titulo_elem: titulo_elem = produto.find('h3')
                
                if not titulo_elem: continue
                titulo = titulo_elem.text.strip()

                # LINK
                link_elem = produto.find('a', class_='ui-search-link')
                if not link_elem: link_elem = produto.find('a')
                link = link_elem['href'] if link_elem else "Link não encontrado"

                # PREÇO
                preco_final = 0.0
                price_container = produto.find('div', class_='ui-search-price__second-line')
                if not price_container: price_container = produto
                
                preco_elem = price_container.find('span', class_='andes-money-amount__fraction')
                if preco_elem:
                    preco_final = limpar_preco(preco_elem.text)
                
                if preco_final < 500: continue

                # LOCALIZAÇÃO
                texto_completo = produto.text.lower()
                tem_frete_gratis = "frete grátis" in texto_completo or "chegará grátis" in texto_completo
                local_elem = produto.find('span', class_='ui-search-item__location')
                localizacao = local_elem.text.strip() if local_elem else "Local não informado"

                resultados.append({
                    'modelo_buscado': modelo,
                    'titulo': titulo,
                    'preco': preco_final,
                    'link': link,
                    'tem_frete': tem_frete_gratis,
                    'localizacao': localizacao,
                    'site': 'Mercado Livre'
                })

            except Exception as e:
                continue

    except Exception as e:
        print(f"Erro no Scraper: {e}")
    
    finally:
        driver.quit()

    return resultados

if __name__ == "__main__":
    # Teste rápido
    dados = buscar_mercadolivre("Roland FP-30X")
    print(f"Encontrados: {len(dados)}")