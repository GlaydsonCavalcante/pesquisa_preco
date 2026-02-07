import time
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Importar a nova função verificar_se_ja_existe
from src.database import criar_tabela, salvar_no_banco, verificar_se_ja_existe
from src.scraper import buscar_mercadolivre
from src.stores_br import executar_busca_lojas_br
from src.ai_validator import validar_com_ia
from src.discovery_engine import executar_descoberta

INICIO_EXECUCAO = time.time()

STATS = {
    "total": 0, "novo": 0, "otimo_estado": 0, "funcional": 0, 
    "semifuncional": 0, "nao_funcional": 0, "ignorados": 0 # Novo contador
}

COOLDOWNS = {"mercadolivre": 600, "lojas_br": 60}
ultima_busca = {"mercadolivre": 0, "lojas_br": 0}

def obter_status_painel():
    delta = time.time() - INICIO_EXECUCAO
    tempo_str = str(timedelta(seconds=int(delta)))
    return (
        f"⏱️ {tempo_str} | 🎹 Capturados: {STATS['total']} | ♻️ Ignorados: {STATS['ignorados']} "
        f"[🆕 {STATS['novo']} | ✨ {STATS['otimo_estado']} | 🆗 {STATS['funcional']}]"
    )

def gerar_termos_busca(modelo_completo):
    termos = [modelo_completo]
    partes = modelo_completo.split()
    if len(partes) > 1:
        termos.append(" ".join(partes[1:]))
    return termos

def processar_modelo(modelo_info):
    modelo_oficial = modelo_info['modelo']
    termos_para_testar = gerar_termos_busca(modelo_oficial)
    agora = time.time()
    
    print(f"\n{'='*80}")
    print(obter_status_painel())
    print(f"🔎 Monitorando: {modelo_oficial} (Score: {modelo_info.get('score_geral', 'N/A')})")
    print(f"{'='*80}")

    # --- 1. LOJAS BR ---
    if agora - ultima_busca["lojas_br"] > COOLDOWNS["lojas_br"]:
        termo_loja = termos_para_testar[-1]
        print(f"🏬 Lojas BR ('{termo_loja}')...", end=" ")
        
        novos = executar_busca_lojas_br(modelo_oficial)
        
        for item in novos:
            # --- OTIMIZAÇÃO: Se já existe no banco, PULA ---
            if verificar_se_ja_existe(item['link']):
                STATS['ignorados'] += 1
                continue

            item['data'] = datetime.now().strftime("%Y-%m-%d")
            item['localizacao'] = 'Loja Oficial'
            item['tem_envio'] = True
            item['estado_detalhado'] = 'novo'
            item['ai_analise'] = 'Loja Confiável'
            
            salvar_no_banco(item)
            STATS['novo'] += 1
            STATS['total'] += 1
            print(".", end="")
            
        print(f" Novos salvos: {len(novos)}")
        ultima_busca["lojas_br"] = time.time()
    else:
        print(f"⏩ Pulando Lojas BR (Cooldown)")

    # --- 2. MERCADO LIVRE ---
    if agora - ultima_busca["mercadolivre"] > COOLDOWNS["mercadolivre"]:
        termo_ml = termos_para_testar[-1]
        print(f"📦 Mercado Livre ('{termo_ml}')...")
        
        time.sleep(random.uniform(5, 8)) 
        usados = buscar_mercadolivre(modelo_oficial, termo_ml)
        
        itens_salvos = 0
        
        for item in usados:
            # --- OTIMIZAÇÃO: VERIFICA DB ANTES DA IA ---
            if verificar_se_ja_existe(item['link']):
                print(f"   ♻️ Já monitorado: {item['titulo'][:30]}...")
                STATS['ignorados'] += 1
                continue # Pula para o próximo sem gastar LLM
            
            # Se é novo, chama a IA
            analise = validar_com_ia(item['titulo'], item['preco'], modelo_oficial)
            
            if analise['valido']:
                estado = analise['estado']
                ativo = 0 if estado == 'nao_funcional' else 1
                
                item['data'] = datetime.now().strftime("%Y-%m-%d")
                item['condicao'] = 'Usado'
                item['loja'] = 'Mercado Livre'
                item['estado_detalhado'] = estado
                item['custo_reparo'] = analise['reparo']
                item['ai_analise'] = analise['motivo']
                item['ativo'] = ativo
                
                salvar_no_banco(item)
                itens_salvos += 1
                STATS['total'] += 1
                if estado in STATS: STATS[estado] += 1
                
                print(f"   ✅ SALVO: R$ {item['preco']:,.0f} | {estado}")
            else:
                pass 
        
        print(f"   -> {itens_salvos} novos capturados.")
        ultima_busca["mercadolivre"] = time.time()
    else:
        print(f"⏩ Pulando ML (Cooldown)")

def ciclo_continuo():
    print(f"🤖 Piano Scout v3.3 (Otimizado + Blindado) Iniciado!")
    
    while True:
        try:
            # 1. Fase de Descoberta (Opcional - pode comentar se quiser só monitorar)
            # print("\n--- 🚀 FASE DE DESCOBERTA ---")
            # executar_descoberta() 

            print("\n--- 🔄 ATUALIZANDO BASE ---")
            df_completo = pd.read_csv('data/modelos_alvo.csv')
            df = df_completo[df_completo['score_geral'] >= 50].copy()
            print(f"📋 {len(df)} modelos qualificados.")
            
        except Exception as e:
            print(f"❌ Erro CSV: {e}")
            time.sleep(60)
            continue

        lista_modelos = df.to_dict('records')
        random.shuffle(lista_modelos)
        
        for modelo_info in lista_modelos:
            processar_modelo(modelo_info)
            print("   --- Pausa de 30s ---")
            time.sleep(30)

if __name__ == "__main__":
    criar_tabela()
    ciclo_continuo()