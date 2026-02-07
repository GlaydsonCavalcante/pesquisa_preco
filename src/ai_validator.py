from google import genai
from google.genai import types
import time
import json
import os
from dotenv import load_dotenv

# Carrega a chave segura do arquivo .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("⚠️ ERRO: Chave API não encontrada no arquivo .env")

# --- NOVA INICIALIZAÇÃO (Padrão 2026) ---
# A biblioteca nova usa um 'Client' centralizado
client = genai.Client(api_key=API_KEY)

def validar_com_ia(titulo_anuncio, price, modelo_alvo):
    prompt = f"""
    Analise este anúncio de instrumento musical.
    Produto Alvo: {modelo_alvo}
    Anúncio: {titulo_anuncio} | Preço: R$ {price}
    
    Classifique em JSON:
    {{
        "eh_o_piano_real": boolean, (False se for peça/aula/acessório/golpe)
        "estado": "string", (Escolha um: 'novo', 'otimo_estado', 'funcional', 'semifuncional', 'nao_funcional')
        "custo_reparo_estimado": float, (Se 'semifuncional' ou 'nao_funcional', estime valor de conserto no Brasil. Se ok, 0)
        "motivo": "string curta"
    }}
    
    Regras de Estado:
    - novo: Lacrado/Loja.
    - otimo_estado: Usado mas perfeito visual e funcional.
    - funcional: Marcas de uso, mas funciona 100%.
    - semifuncional: Tecla falhando, som baixo, defeito leve.
    - nao_funcional: Não liga, defeito grave.
    """

    try:
        # Pausa técnica para evitar rate-limit
        time.sleep(1)
        
        # --- CHAMADA ATUALIZADA ---
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', # Atualizado para o modelo da tua lista
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1, # Respostas frias e diretas
                response_mime_type='application/json' # Garante que volta JSON puro
            )
        )
        
        # Na nova lib, response.text já traz o conteúdo limpo
        resultado = json.loads(response.text)
        
        return {
            "valido": resultado.get('eh_o_piano_real', False),
            "estado": resultado.get('estado', 'indefinido'),
            "reparo": resultado.get('custo_reparo_estimado', 0),
            "motivo": resultado.get('motivo', 'Sem motivo')
        }

    except Exception as e:
        # Captura erro de bloqueio de segurança ou rede
        print(f"⚠️ Erro IA: {e}")
        return {"valido": False, "motivo": f"Erro Técnico: {str(e)[:50]}...", "reparo": 0, "estado": "erro"}

# Teste Rápido (Só roda se executares este arquivo direto)
if __name__ == "__main__":
    print("Teste de conexão com Gemini 2.5 Flash...")
    res = validar_com_ia("Piano Digital Roland Fp-30x Usado", 3500.00, "Roland FP-30X")
    print(res)

# src/ai_validator.py

def analisar_novo_modelo_ahsd(nome_modelo, titulo_anuncio):
    prompt = f"""
    ###CONTEXTO
    Atue como um especialista em engenharia de instrumentos musicais para usuários com Altas Habilidades/Superdotação (QI 140+). 
    Sua tarefa é avaliar um novo modelo de piano digital utilizando estritamente a mesma régua técnica aplicada anteriormente.
    Os Critérios de Pontuação (0-100) são:
    Fidelidade Mecânica (Peso 45%): Sensores triplos, escapamento (let-off), pivot e realismo do martelo.
    Riqueza Harmônica e Polifonia (Peso 30%): Modelagem de ressonância e teto de polifonia (mínimo ideal > 128). 
    Capacidade de Parametrização (Peso 25%): Profundidade de edição (EQ, compressores, Virtual Technician). 

    Utilize os seguintes exemplos como BASE DE CALIBRAÇÃO (Yardstick):
    modelo,mecanica,som_polifonia,customizacao,score_geral,justificativa
    Roland FP-90X,98,96,92,96,"Ação PHA-50 híbrida e polifonia ilimitada para piano, ideal para processamento sensorial de alta fidelidade."
    Roland FP-30X,88,85,80,85,"Polifonia de 256 notas e ação PHA-4, garantindo longevidade técnica para estudos avançados."
    Nux NPK-20,83,82,97,86,"Insuperável em parametrização na sua faixa, com equalizador de 9 bandas e compressão ajustável."
    Kawai ES120,82,89,78,83,"Motor Harmonic Imaging com Virtual Technician para ajuste fino de 17 parâmetros de ressonância."
    Yamaha P-145,72,65,60,67,"Polifonia de 64 notas é um gargalo para a capacidade de processamento AHSD."
    Casio CDP-S110,65,68,40,60,"Mecânica simplificada com pivot curto que pode frustrar a evolução rápida."

    ###DADOS PARA ANÁLISE
    Avalie o modelo: {nome_modelo} baseado nos dados: {titulo_anuncio}.

    ###INSTRUÇÕES DE RESPOSTA
    Gere uma tabela de notas para o novo modelo.
    Calcule o Score Geral AHSD ponderado.
    Apresente uma Justificativa Analítica comparando o novo modelo com os marcos acima 
        (ex: 'Mecânica italiana Fatar e polifonia de 512 notas, oferecendo teto técnico elevado.')
        (ex: 'Motor T2L com amostragem XXL de 15 segundos sem loops, detectável por ouvidos AHSD.')
    Dê um Veredito de Investimento focado em evitar o 'gasto duplo' para um aluno que aprende rápido.
    Responda estritamente em JSON:
    {{
        "modelo": "{nome_modelo}",
        "mecanica": int,
        "som_polifonia": int,
        "customizacao": int,
        "score_geral": float,
        "justificativa": "Análise comparativa curta",
        "veredito": "Explicação sobre evitar gasto duplo",
        "priorizado": false
    }}
    """
   
    try:
        # Chamada ao cliente Gemini (Flash Lite ou Preview)
        response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type='application/json'
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"⚠️ Erro na análise AHSD: {e}")
        return None
