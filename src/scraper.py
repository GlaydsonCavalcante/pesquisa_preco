import requests
from bs4 import BeautifulSoup
import time
import random

# Configuração para "enganar" o site e parecer um navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def buscar_mercadolivre(modelo):
    """
    Busca um modelo específico no Mercado Livre e retorna uma lista de produtos encontrados.
    """
    print(f"--- Pesquisando por: {modelo} no Mercado Livre ---")
    
    # Prepara o termo de busca para a URL (ex: 'Roland FP-30X' vira 'Roland-FP-30X')
    termo_url = modelo.replace(" ", "-")
    url = f"https://lista.mercadolivre.com.br/instrumentos-musicais/{termo_url}_NoIndex_True"

    try:
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            print(f"Erro ao acessar a página. Código: {response.status_code}")
            return []

        # O 'sopa' (soup) é o objeto que contém o HTML da página organizado
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Encontra todos os cartões de produtos (a classe pode mudar, mas esta é a padrão atual)
        produtos_html = soup.find_all('li', class_='ui-search-layout__item')
        
        resultados = []

        for produto in produtos_html:
            try:
                # 1. Título
                titulo_elem = produto.find('h2', class_='ui-search-item__title')
                if not titulo_elem: continue # Pula se não tiver título
                titulo = titulo_elem.text.strip()

                # 2. Link
                link_elem = produto.find('a', class_='ui-search-link')
                link = link_elem['href']

                # 3. Preço
                # O preço no ML é dividido em partes, pegamos o container de preço
                preco_elem = produto.find('span', class_='andes-money-amount__fraction')
                preco_texto = preco_elem.text.replace('.', '').strip() if preco_elem else "0"
                
                # 4. Frete e Localização (Informações extras)
                # Procuramos textos que indiquem frete ou local
                infos_extras = produto.text
                tem_frete_gratis = "Frete grátis" in infos_extras or "Chegará grátis" in infos_extras
                
                # Adiciona à lista de resultados
                resultados.append({
                    'modelo_buscado': modelo,
                    'titulo': titulo,
                    'preco': float(preco_texto),
                    'link': link,
                    'tem_frete': tem_frete_gratis,
                    'site': 'Mercado Livre'
                })

            except Exception as e:
                # Se der erro num item específico, pula para o próximo mas avisa
                # print(f"Erro ao ler um item: {e}") 
                continue

        print(f"Encontrados {len(resultados)} anúncios para {modelo}.")
        return resultados

    except Exception as e:
        print(f"Erro crítico na busca: {e}")
        return []

# --- ÁREA DE TESTE ---
# Este bloco só roda se executares o arquivo diretamente. 
# Serve para testar se o scraper está a funcionar.
if __name__ == "__main__":
    # Teste com um dos modelos da tua lista
    teste = buscar_mercadolivre("Roland FP-30X")
    
    # Mostra os 3 primeiros resultados encontrados
    print("\n--- RESULTADOS DO TESTE (Top 3) ---")
    for item in teste[:3]:
        print(f"Produto: {item['titulo']}")
        print(f"Preço: R$ {item['preco']}")
        print(f"Frete Grátis? {'Sim' if item['tem_frete'] else 'Não detectado'}")
        print("-" * 30)