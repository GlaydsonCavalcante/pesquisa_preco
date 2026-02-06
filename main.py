import time
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import criar_tabela, salvar_no_banco
from scraper import buscar_mercadolivre
from stores_br import executar_busca_lojas_br
from ai_validator import validar_com_ia
from discovery_engine import executar_descoberta

def job():
    print("\n--- 🚀 INICIANDO NOVA BATERIA DE BUSCAS ---")
    
    # 1. Antes de buscar preços, tenta descobrir modelos novos
    try:
        executar_descoberta()
    except Exception as e:
        print(f"⚠️ Falha na fase de descoberta: {e}")

    # 2. Segue com a rotina principal de monitoramento de preços
    rotina_principal()
    
# --- VARIÁVEIS GLOBAIS DE CONTROLE ---
INICIO_EXECUCAO = time.time()

# Estatísticas da Sessão Atual
STATS = {
    "total": 0,
    "novo": 0,
    "otimo_estado": 0,
    "funcional": 0,
    "semifuncional": 0,
    "nao_funcional": 0
}

COOLDOWNS = {
    "mercadolivre": 600, 
    "lojas_br": 60,
}

ultima_busca = {
    "mercadolivre": 0,
    "lojas_br": 0
}

def obter_status_painel():
    """Gera a string do painel com tempo e contadores."""
    # Calcula tempo decorrido
    delta = time.time() - INICIO_EXECUCAO
    tempo_str = str(timedelta(seconds=int(delta)))
    
    # Formata os contadores
    # Ex: [Total: 12] (Novo: 2 | Ótimo: 5 | Func: 3 | Semi: 1 | Ruim: 1)
    status = (
        f"⏱️ {tempo_str} | 🎹 Pianos: {STATS['total']} "
        f"[🆕 {STATS['novo']} | ✨ {STATS['otimo_estado']} | 🆗 {STATS['funcional']} | ⚠️ {STATS['semifuncional']}]"
    )
    return status

def gerar_termos_busca(modelo_completo):
    termos = [modelo_completo]
    partes = modelo_completo.split()
    if len(partes) > 1:
        # Adiciona versão sem a marca (ex: FP-30X)
        termo_sem_marca = " ".join(partes[1:])
        termos.append(termo_sem_marca)
    return termos

def processar_modelo(modelo_info):
    modelo_oficial = modelo_info['modelo']
    termos_para_testar = gerar_termos_busca(modelo_oficial)
    agora = time.time()
    
    # Imprime o Painel antes de começar o modelo
    print(f"\n{'='*80}")
    print(obter_status_painel())
    print(f"🔎 Analisando agora: {modelo_oficial}")
    print(f"{'='*80}")

    # --- 1. LOJAS BR ---
    if agora - ultima_busca["lojas_br"] > COOLDOWNS["lojas_br"]:
        termo_loja = termos_para_testar[-1]
        print(f"🏬 Lojas BR ('{termo_loja}')...", end=" ")
        
        # Nota: Se o teu stores_br não aceitar 2 argumentos, usa só modelo_oficial
        novos = executar_busca_lojas_br(modelo_oficial) 
        
        if novos:
            print(f"Encontrados: {len(novos)}")
            for item in novos:
                item['data'] = datetime.now().strftime("%Y-%m-%d")
                item['localizacao'] = 'Loja Oficial'
                item['tem_envio'] = True
                item['estado_detalhado'] = 'novo'
                item['ai_analise'] = 'Loja Confiável'
                
                salvar_no_banco(item)
                
                # Atualiza Stats
                STATS['novo'] += 1
                STATS['total'] += 1
        else:
            print("Nenhum.")
        
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
                
                # Atualiza Stats Dinamicamente
                STATS['total'] += 1
                if estado in STATS:
                    STATS[estado] += 1
                
                icones = {
                    'novo': '🆕', 'otimo_estado': '✨', 'funcional': '🆗', 
                    'semifuncional': '⚠️', 'nao_funcional': '💀'
                }
                icone = icones.get(estado, '❓')
                
                print(f"   ✅ {icone} {estado.upper()}: R$ {item['preco']:,.0f}")
            else:
                # Opcional: print(f"   ❌ Lixo: {analise['motivo']}")
                pass
        
        print(f"   -> {itens_salvos} capturados.")
        ultima_busca["mercadolivre"] = time.time()
    else:
        print(f"⏩ Pulando ML (Cooldown)")

def ciclo_continuo():
    try:
        df = pd.read_csv('data/modelos_alvo.csv')
    except:
        print("Erro: data/modelos_alvo.csv não encontrado.")
        return

    print(f"🤖 Piano Scout v3.1 (Com Monitoramento) Iniciado!")
    
    while True:
        lista_modelos = df.to_dict('records')
        random.shuffle(lista_modelos)
        
        for modelo_info in lista_modelos:
            processar_modelo(modelo_info)
            print("   --- Pausa de 30s ---")
            time.sleep(30)

if __name__ == "__main__":
    criar_tabela()
    ciclo_continuo()