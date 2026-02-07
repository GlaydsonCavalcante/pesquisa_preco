import pandas as pd
import os
import time
import csv  # <--- IMPORTANTE: Adicionado para controlar as aspas
from datetime import datetime
from ai_validator import analisar_novo_modelo_ahsd
from scraper import buscar_mercadolivre 

def executar_descoberta():
    CSV_PATH = os.path.join('data', 'modelos_alvo.csv')
    start_time = time.time()
    count_avaliados = 0
    count_aprovados = 0
    
    print(f"\n🚀 [DISCOVERY ENGINE] Iniciado em {datetime.now().strftime('%H:%M:%S')}")
    
    buscas = ["Piano Digital 88 teclas pesado", "Piano Digital Hammer Action"]
    
    for termo in buscas:
        print(f"\n🔎 Varrendo Mercado Livre: '{termo}'")
        itens = buscar_mercadolivre("DESCOBERTA", termo)
        
        for item in itens:
            # Recarrega a base com tratamento de erro robusto
            try:
                df_atual = pd.read_csv(CSV_PATH, on_bad_lines='skip') # <--- Proteção na leitura
            except:
                df_atual = pd.DataFrame(columns=['modelo']) # Fallback se o arquivo sumir
                
            modelos_na_base = df_atual['modelo'].str.upper().tolist()
            
            titulo_original = item['titulo']
            nome_sugerido = " ".join(titulo_original.split()[:4]).upper()
            
            # 1. VERIFICAÇÃO DE MEMÓRIA
            if any(m in nome_sugerido for m in modelos_na_base):
                continue
                
            # 2. ANÁLISE PELA IA
            count_avaliados += 1
            print(f"✨ [{count_avaliados}] Analisando novo candidato: {nome_sugerido}...")
            
            analise = analisar_novo_modelo_ahsd(nome_sugerido, titulo_original)
            
            if isinstance(analise, list) and len(analise) > 0: analise = analise[0]

            if analise and isinstance(analise, dict) and 'score_geral' in analise:
                score = analise['score_geral']
                justificativa = analise.get('justificativa', 'Sem justificativa')
                veredito = analise.get('veredito', '')
                
                # 3. LOG DE DECISÃO NA TELA
                if score >= 50:
                    status_icon = "✅"
                    status_msg = f"APROVADO | Score: {score}"
                    count_aprovados += 1
                else:
                    status_icon = "❌"
                    status_msg = f"REJEITADO | Score: {score}"
                
                print(f"   {status_icon} {status_msg}")
                print(f"   📝 Motivo: {justificativa[:100]}...") # Trunca na tela para não poluir

                # 4. REGISTRO SEGURO NO CSV
                nova_linha = {
                    "modelo": analise['modelo'],
                    "mecanica": analise['mecanica'],
                    "som_polifonia": analise['som_polifonia'],
                    "customizacao": analise['customizacao'],
                    "score_geral": score,
                    "justificativa": f"{justificativa} | Veredito: {veredito}",
                    "priorizado": False
                }
                
                df_temp = pd.DataFrame([nova_linha])
                
                # AQUI ESTÁ A CORREÇÃO CRUCIAL: quoting=csv.QUOTE_NONNUMERIC
                df_temp.to_csv(
                    CSV_PATH, 
                    mode='a', 
                    header=False, 
                    index=False, 
                    quoting=csv.QUOTE_NONNUMERIC 
                )
            
            if count_avaliados % 5 == 0:
                elapsed = time.time() - start_time
                print(f"\n--- ⏱️ Status: {count_avaliados} avaliados | {count_aprovados} novos | {elapsed:.0f}s ---")

            time.sleep(1.5)

    total_time = time.time() - start_time
    print(f"\n🏁 Descoberta finalizada em {total_time:.0f}s. Novos modelos: {count_aprovados}")

if __name__ == "__main__":
    executar_descoberta()