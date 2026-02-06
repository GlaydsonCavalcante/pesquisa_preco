import time
import pandas as pd
from datetime import datetime
import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import criar_tabela, salvar_no_banco
from scraper import buscar_mercadolivre
from stores_br import executar_busca_lojas_br
from ai_validator import validar_com_ia

# CONFIGURAÇÃO DE TIMERS (Em segundos)
COOLDOWNS = {
    "mercadolivre": 600,  # 10 min entre buscas no ML
    "lojas_br": 60,       # 1 min entre buscas em lojas (mais tolerantes)
}

# Controle de quando foi a última busca em cada site
ultima_busca = {
    "mercadolivre": 0,
    "lojas_br": 0
}

def processar_modelo(modelo_info):
    modelo = modelo_info['modelo']
    agora = time.time()
    
    # --- 1. LOJAS BR (Ninja Som / Tecla) ---
    # Verifica se já passou tempo suficiente desde a última busca
    if agora - ultima_busca["lojas_br"] > COOLDOWNS["lojas_br"]:
        print(f"\n🏬 Consultando Lojas BR: {modelo}...")
        novos = executar_busca_lojas_br(modelo)
        for item in novos:
            item['data'] = datetime.now().strftime("%Y-%m-%d")
            item['localizacao'] = 'Loja Oficial'
            item['tem_envio'] = True
            item['estado_detalhado'] = 'novo'
            item['ai_analise'] = 'Loja Confiável'
            salvar_no_banco(item)
        
        ultima_busca["lojas_br"] = time.time() # Atualiza relógio
    else:
        print(f"⏩ Pulando Lojas BR (Cooldown ativo)")

    # --- 2. MERCADO LIVRE ---
    if agora - ultima_busca["mercadolivre"] > COOLDOWNS["mercadolivre"]:
        print(f"\n📦 Consultando Mercado Livre: {modelo}...")
        
        # Pausa "humana" antes de entrar
        time.sleep(random.uniform(5, 10)) 
        
        usados = buscar_mercadolivre(modelo)
        
        for item in usados:
            # IA ANALISA O ESTADO
            analise = validar_com_ia(item['titulo'], item['preco'], modelo)
            
            if analise['valido']:
                # Se for não funcional, salvamos mas já inativamos (ativo=0) para não poluir gráfico
                ativo = 0 if analise['estado'] == 'nao_funcional' else 1
                
                item['data'] = datetime.now().strftime("%Y-%m-%d")
                item['condicao'] = 'Usado'
                item['loja'] = 'Mercado Livre'
                item['estado_detalhado'] = analise['estado']
                item['custo_reparo'] = analise['reparo']
                item['ai_analise'] = analise['motivo']
                item['ativo'] = ativo
                
                salvar_no_banco(item)
                print(f"   ✅ {analise['estado'].upper()}: {item['titulo'][:20]}...")
            else:
                print(f"   ❌ Rejeitado: {analise['motivo']}")

        ultima_busca["mercadolivre"] = time.time() # Atualiza relógio
    else:
        print(f"⏩ Pulando Mercado Livre (Cooldown ativo)")

def ciclo_continuo():
    try:
        df = pd.read_csv('data/modelos_alvo.csv')
    except:
        print("Erro CSV.")
        return

    print("🤖 Piano Scout Otimizado Iniciado...")
    
    while True:
        # Embaralha modelos a cada ciclo completo
        lista_modelos = df.to_dict('records')
        random.shuffle(lista_modelos)
        
        for modelo_info in lista_modelos:
            processar_modelo(modelo_info)
            
            # Pequena pausa entre modelos para não travar CPU
            print("   --- Aguardando 30s para trocar modelo ---")
            time.sleep(30)
            
        print("\n💤 Ciclo de modelos concluído. Verificando timers...")

if __name__ == "__main__":
    criar_tabela()
    ciclo_continuo()