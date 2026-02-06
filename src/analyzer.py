import pandas as pd
import re
from datetime import datetime
from scraper import buscar_mercadolivre

# Lista de exclusão (peças e acessórios)
PALAVRAS_PROIBIDAS = [
    'placa', 'main board', 'botão', 'knob', 'suporte', 'capa', 'bag', 'case', 
    'pedal', 'estante', 'móvel', 'banco', 'banqueta', 'fonte', 'adesivo', 
    'cobertura', 'stand', 'rack', 'pedaleira', 'triplo', 'cover'
]

PRECO_MINIMO_ACEITAVEL = 1500.00 

def carregar_modelos():
    try:
        return pd.read_csv('data/modelos_alvo.csv')
    except Exception as e:
        print(f"Erro CSV: {e}")
        return pd.DataFrame()

def limpar_string(texto):
    """Remove espaços, traços e deixa minúsculo para comparação."""
    return re.sub(r'[^a-z0-9]', '', str(texto).lower())

def validar_correspondencia_modelo(modelo_alvo, titulo_anuncio):
    """
    Garante que o modelo buscado está REALMENTE no título.
    Ex: Se busco 'P-225', rejeita 'Yamaha P-45'.
    """
    # Simplifica as strings (ex: "P-225" vira "p225")
    alvo_limpo = limpar_string(modelo_alvo)
    titulo_limpo = limpar_string(titulo_anuncio)
    
    # Estratégia de "Tokens" para modelos compostos (ex: FP-30X)
    # Quebra o modelo em partes. Ex: "Roland FP-30X" -> ["roland", "fp30x"]
    # Verifica se a parte mais específica (o número do modelo) está no título.
    partes_modelo = modelo_alvo.split()
    
    # Pega o último termo (geralmente é o modelo específico: 'FP-30X', 'P-225', 'ES120')
    termo_chave = limpar_string(partes_modelo[-1]) 
    
    if termo_chave in titulo_limpo:
        return True
    
    return False

def eh_produto_valido(titulo, preco, modelo_alvo):
    # 1. Filtro de Preço
    if preco < PRECO_MINIMO_ACEITAVEL: return False
        
    # 2. Filtro de Palavras Proibidas
    titulo_lower = titulo.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in titulo_lower: return False
            
    # 3. Filtro de Identidade (Novo!)
    if not validar_correspondencia_modelo(modelo_alvo, titulo):
        return False

    return True

def calcular_oportunidade(preco, score_geral):
    if score_geral == 0: return 0
    return round(preco / score_geral, 2)

def executar_analise_geral():
    print("--- 🧠 INICIANDO ANÁLISE (COM AUDITORIA DE MODELO) ---")
    
    df_modelos = carregar_modelos()
    if df_modelos.empty: return []

    oportunidades = []

    for index, row in df_modelos.iterrows():
        modelo_nome = row['modelo']
        score = row['score_geral']
        
        resultados_web = buscar_mercadolivre(modelo_nome)
        
        for item in resultados_web:
            # Agora passamos o 'modelo_nome' para validar
            if not eh_produto_valido(item['titulo'], item['preco'], modelo_nome):
                continue
            
            # Lógica de Logística
            passou_logistica = item['tem_frete'] or \
                               "distrito federal" in item['localizacao'].lower() or \
                               "brasília" in item['localizacao'].lower()
            
            # Se quiseres ser rigoroso e só aceitar o que passa na logística, descomenta:
            # if not passou_logistica: continue 

            indice = calcular_oportunidade(item['preco'], score)
            
            oportunidades.append({
                'data': datetime.now().strftime("%Y-%m-%d"),
                'modelo': modelo_nome,
                'titulo': item['titulo'], 
                'preco': item['preco'],
                'score': score,
                'indice': indice, 
                'tem_frete': item['tem_frete'],
                'local': item['localizacao'],
                'link': item['link']
            })

    df_resultados = pd.DataFrame(oportunidades)
    
    if not df_resultados.empty:
        df_resultados = df_resultados.sort_values(by='indice')
    
    return df_resultados

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    df = executar_analise_geral()
    
    print("\n\n🎹 --- MELHORES OPORTUNIDADES (Auditadas) --- 🎹")
    
    if not df.empty:
        top_5 = df.head(5)
        for i, row in top_5.iterrows():
            print(f"\n🏆 RANK #{i+1} | {row['modelo']}")
            print(f"   💲 R$ {row['preco']:,.2f} (Score: {row['score']})")
            print(f"   📦 {row['titulo']}")
            print(f"   🔗 {row['link']}")
            print("-" * 60)
        print(f"\nTotal encontrado: {len(df)}")
    else:
        print("Nenhum piano passou nos critérios rigorosos hoje.")