import pandas as pd
import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from scraper import buscar_mercadolivre # Usaremos a base do scraper que já temos
from ai_validator import analisar_novo_modelo_ahsd

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def executar_descoberta():
    CSV_PATH = 'data/modelos_alvo.csv'
    df_alvo = pd.read_csv(CSV_PATH)
    modelos_conhecidos = df_alvo['modelo'].str.upper().tolist()
    
    print("\n🚀 Iniciando Motor de Descoberta (Busca por novos horizontes)...")
    
    # Busca genérica para encontrar o que não conhecemos
    buscas_genericas = ["Piano Digital 88 teclas pesado", "Piano Digital Profissional"]
    novos_candidatos = []

    for busca in buscas_genericas:
        print(f"🔎 Varrendo: {busca}")
        itens = buscar_mercadolivre("DESCOBERTA", busca) # Reutiliza seu scraper
        
        for item in itens:
            titulo = item['titulo'].upper()
            # Se o modelo não está no CSV e parece ser um piano (preço > 2500 para filtrar lixo)
            if not any(m in titulo for m in modelos_conhecidos) and item['preco'] > 2000:
                # Extrai um possível nome de modelo (as primeiras 4 palavras costumam ajudar)
                nome_sugerido = " ".join(item['titulo'].split()[:4])
                
                if nome_sugerido not in [n['modelo'] for n in novos_candidatos]:
                    print(f"✨ Novo modelo detectado: {nome_sugerido}. Analisando via AHSD...")
                    analise = analisar_novo_modelo_ahsd(nome_sugerido, item['titulo'])
                    
                    if analise and analise['score_geral'] >= 70: # Só adiciona se for digno
                        print(f"✅ Modelo Aprovado! Score: {analise['score_geral']}")
                        novos_candidatos.append(analise)
                    else:
                        print(f"📉 Modelo Rejeitado pela régua técnica.")
    
    if novos_candidatos:
        df_novos = pd.DataFrame(novos_candidatos)
        df_final = pd.concat([df_alvo, df_novos], ignore_index=True)
        df_final.to_csv(CSV_PATH, index=False)
        print(f"📝 {len(novos_candidatos)} novos modelos adicionados ao seu CSV de monitoramento!")
    else:
        print("📭 Nenhum modelo novo relevante encontrado nesta rodada.")

if __name__ == "__main__":
    executar_descoberta()