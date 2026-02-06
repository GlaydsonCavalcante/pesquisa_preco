import google.generativeai as genai
import time
import json

# CONFIGURAÇÃO DA IA
# Substitua pela sua API KEY real
API_KEY = "COLOQUE_SUA_API_KEY_AQUI"

genai.configure(api_key=API_KEY)

# Configuração do Modelo (Flash é mais barato e rápido)
generation_config = {
  "temperature": 0.1, # Muito baixa para ser "frio" e preciso
  "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

def validar_com_ia(titulo_anuncio, price, modelo_alvo):
    """
    Usa o Gemini para decidir se o anúncio é realmente o piano ou apenas uma peça.
    """
    prompt = f"""
    Atue como um especialista em instrumentos musicais.
    Analise este anúncio do Mercado Livre:
    
    Produto Alvo: Piano Digital {modelo_alvo}
    Título do Anúncio: {titulo_anuncio}
    Preço: R$ {price}
    
    Responda em formato JSON:
    {{
        "eh_o_piano_real": boolean,  // True se for o instrumento completo, False se for peça/aula/acessório/golpe
        "motivo": "string curta explicando"
    }}
    
    Regras:
    1. Se for apenas estante, pedal, capa, fonte, placa, ou aula, é FALSE.
    2. Se o preço for absurdamente baixo (ex: menos de R$ 1000 para um piano de R$ 5000), é FALSE (suspeita de peça ou golpe).
    3. Se for o piano (mesmo usado), é TRUE.
    """

    try:
        # Pequena pausa para não estourar cota da API se rodar muito rápido
        time.sleep(1) 
        
        response = model.generate_content(prompt)
        resultado = json.loads(response.text)
        
        return resultado['eh_o_piano_real'], resultado['motivo']

    except Exception as e:
        print(f"⚠️ Erro na IA: {e}. Assumindo falso por segurança.")
        return False, "Erro na validação IA"

# Teste rápido
if __name__ == "__main__":
    print(validar_com_ia("Capa Para Piano Roland Fp-30x", 250.00, "Roland FP-30X"))
    print(validar_com_ia("Piano Digital Roland Fp-30x Usado", 3800.00, "Roland FP-30X"))