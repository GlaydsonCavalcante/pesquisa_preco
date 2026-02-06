import time
import random
import schedule
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import criar_tabela, salvar_no_banco
from scraper import buscar_mercadolivre
from stores_br import executar_busca_lojas_br
from ai_validator import validar_com_ia

def tarefa_busca_modelo(modelo_info):
    """Executa a busca para UM único modelo e salva."""
    modelo = modelo_info['modelo']
    score = modelo_info['score_geral']
    
    print(f"\n⏰ {datetime.now().strftime('%H:%M')} - Iniciando ciclo suave para: {modelo}")
    
    # 1. Busca Referência de Novo (Ninja Som / Tecla)
    # Não usamos IA aqui pois a loja é confiável
    print(f"   Searching Lojas BR...")
    novos = executar_busca_lojas_br(modelo)
    for item in novos:
        item['data'] = datetime.now().strftime("%Y-%m-%d")
        item['localizacao'] = 'Loja Oficial'
        item['tem_envio'] = True
        item['ai_analise'] = 'Loja Confiável (Ninja/Tecla)'
        salvar_no_banco(item)

    # 2. Busca Usados (Mercado Livre)
    print(f"   Searching Mercado Livre...")
    usados = buscar_mercadolivre(modelo)
    
    count_validos = 0
    for item in usados:
        # AQUI ENTRA O GEMINI
        eh_valido, motivo = validar_com_ia(item['titulo'], item['preco'], modelo)
        
        if eh_valido:
            item['data'] = datetime.now().strftime("%Y-%m-%d")
            item['condicao'] = 'Usado'
            item['loja'] = 'Mercado Livre'
            item['ai_analise'] = motivo
            salvar_no_banco(item)
            count_validos += 1
            print(f"      ✅ Aprovado IA: {item['titulo'][:30]}... (R$ {item['preco']})")
        else:
            print(f"      ❌ Rejeitado IA: {item['titulo'][:30]}... ({motivo})")

    print(f"   💤 Ciclo finalizado para {modelo}. {count_validos} itens salvos.")

def rotina_principal():
    """Lê o CSV e agenda as buscas de forma espaçada."""
    try:
        df = pd.read_csv('data/modelos_alvo.csv')
    except:
        print("Erro ao ler CSV.")
        return

    # Embaralha a lista para não buscar sempre na mesma ordem
    modelos = df.to_dict('records')
    random.shuffle(modelos)

    print(f"--- INICIANDO ROTINA ESPAÇADA PARA {len(modelos)} MODELOS ---")
    
    for i, modelo_info in enumerate(modelos):
        # Executa a busca
        tarefa_busca_modelo(modelo_info)
        
        # Se não for o último, espera um tempão antes do próximo
        if i < len(modelos) - 1:
            tempo_espera = random.randint(600, 1800) # Entre 10 e 30 minutos
            print(f"   ☕ Pausa para café... Próxima busca em {tempo_espera/60:.1f} minutos.")
            time.sleep(tempo_espera)

def job():
    print("\n--- 🚀 INICIANDO NOVA BATERIA DE BUSCAS ---")
    rotina_principal()
    print("--- BATERIA FINALIZADA. AGUARDANDO PRÓXIMO AGENDAMENTO ---")

if __name__ == "__main__":
    criar_tabela()
    
    # Executa uma vez agora ao iniciar
    job()
    
    # Agenda para rodar a cada 6 horas (4 vezes ao dia)
    schedule.every(6).hours.do(job)
    
    print("🤖 O Piano Scout está em modo 'Serviço Contínuo'.")
    print("Pressione Ctrl+C para parar.")
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Verifica o agendamento a cada minuto