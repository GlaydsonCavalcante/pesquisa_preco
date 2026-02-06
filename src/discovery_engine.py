import pandas as pd
import os
import time
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
            # Recarrega a base para saber quem já foi avaliado (incluindo os rejeitados anteriormente)
            df_atual = pd.read_csv(CSV_PATH)
            modelos_na_base = df_atual['modelo'].str.upper().tolist()
            
            titulo_original = item['titulo']
            # Extração simples para checagem rápida
            nome_sugerido = " ".join(titulo_original.split()[:4]).upper()
            
            # 1. VERIFICAÇÃO DE MEMÓRIA (Evita gasto de API)
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
                    status_msg = "APROVADO (Rumo ao Dashboard)"
                    count_aprovados += 1
                else:
                    status_icon = "❌"
                    status_msg = "REJEITADO (Abaixo do teto técnico)"
                
                print(f"   {status_icon} Score: {score} | {status_msg}")
                print(f"   📝 Motivo: {justificativa}")
                if veredito: print(f"   ⚖️ Veredito: {veredito}")

                # 4. REGISTRO NA BASE DE DADOS (Salva todos para memória futura)
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
                df_temp.to_csv(CSV_PATH, mode='a', header=False, index=False)
            
            # 5. MARCADOR DE TEMPO E PROGRESSO (A cada intervalo de itens ou tempo)
            if count_avaliados % 5 == 0:
                elapsed = time.time() - start_time
                print(f"\n--- ⏱️ Progressão: {count_avaliados} analisados | {count_aprovados} aprovados | Tempo: {elapsed:.0f}s ---")

            time.sleep(1.5) # Pausa de segurança para a API

    total_time = time.time() - start_time
    print(f"\n🏁 Descoberta finalizada em {total_time:.0f}s.")
    print(f"📊 Resumo: {count_avaliados} novos modelos catalogados.")

if __name__ == "__main__":
    executar_descoberta()