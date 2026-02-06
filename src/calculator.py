def calcular_importacao(preco_usd, frete_usd, loja_certificada=False):
    """
    Calcula o custo final (Landed Cost) de um produto importado para o Brasil.
    
    Regras Baseadas no 'Remessa Conforme' (Vigência 2024/2025):
    - Abaixo de $50 (Certificado): 20% II + 17% ICMS.
    - Acima de $50 (Certificado): 60% II (com desconto de $20) + 17% ICMS.
    - Não Certificado (Qualquer valor): 60% II + 17% ICMS.
    """
    
    # 1. CONSTANTES DE MERCADO
    TAXA_DOLAR = 6.00      # Podemos automatizar isso depois
    ICMS_ALIQUOTA = 0.17   # Média nacional para e-commerce (17%)
    
    # Valor total em Dólar (Produto + Frete)
    valor_aduaneiro_usd = preco_usd + frete_usd
    
    # 2. DEFINIÇÃO DA ALÍQUOTA DE IMPORTAÇÃO (FEDERAL)
    if loja_certificada:
        if valor_aduaneiro_usd <= 50.00:
            aliquota_ii = 0.20  # 20% para compras pequenas em sites parceiros
            desconto_ii = 0.00
        else:
            aliquota_ii = 0.60  # 60% para compras maiores
            desconto_ii = 20.00 # Desconto padrão de 20 dólares no imposto
    else:
        # Loja não certificada (eBay vendedor comum, Reverb, etc)
        aliquota_ii = 0.60      # Sempre 60%
        desconto_ii = 0.00      # Sem choro
    
    # 3. CÁLCULO DOS IMPOSTOS (EM DÓLAR)
    imposto_importacao_usd = (valor_aduaneiro_usd * aliquota_ii) - desconto_ii
    if imposto_importacao_usd < 0: imposto_importacao_usd = 0

    valor_com_ii = valor_aduaneiro_usd + imposto_importacao_usd

    # 4. A PEGADINHA DO ICMS ("Cálculo por Dentro")
    # O ICMS incide sobre o (Valor + II) dividido por (1 - ICMS)
    base_calculo_icms = valor_com_ii / (1 - ICMS_ALIQUOTA)
    valor_icms_usd = base_calculo_icms * ICMS_ALIQUOTA
    
    # 5. CONVERSÃO FINAL PARA REAIS
    custo_produto_brl = preco_usd * TAXA_DOLAR
    custo_frete_brl = frete_usd * TAXA_DOLAR
    custo_impostos_brl = (imposto_importacao_usd + valor_icms_usd) * TAXA_DOLAR
    
    preco_final_brl = custo_produto_brl + custo_frete_brl + custo_impostos_brl
    
    # Taxa efetiva real (quanto pagas de imposto sobre o produto)
    taxa_efetiva = (custo_impostos_brl / (custo_produto_brl + custo_frete_brl)) * 100

    return {
        "preco_original_brl": round(custo_produto_brl, 2),
        "frete_brl": round(custo_frete_brl, 2),
        "total_impostos_brl": round(custo_impostos_brl, 2),
        "preco_final_brl": round(preco_final_brl, 2),
        "taxa_efetiva_porcentagem": round(taxa_efetiva, 1),
        "detalhes": {
            "regime": "Remessa Conforme" if loja_certificada else "Importação Comum",
            "aliquota_federal": f"{int(aliquota_ii * 100)}%"
        }
    }

# --- ÁREA DE TESTE RÁPIDO ---
if __name__ == "__main__":
    print("--- SIMULAÇÃO DE IMPORTAÇÃO ---")
    
    # CENÁRIO 1: Pedal no AliExpress (Certificado, <$50)
    print("\n1. Pedal Overdrive (US$ 40 + Frete Grátis) - Loja Certificada")
    resultado1 = calcular_importacao(40, 0, loja_certificada=True)
    print(f"   Preço Produto: R$ {resultado1['preco_original_brl']}")
    print(f"   Impostos: R$ {resultado1['total_impostos_brl']} ({resultado1['detalhes']['aliquota_federal']})")
    print(f"   TOTAL NA PORTA: R$ {resultado1['preco_final_brl']}")
    
    # CENÁRIO 2: Piano no eBay (Não Certificado, >$50)
    print("\n2. Piano Digital (US$ 500 + US$ 100 Frete) - Loja Comum (Reverb/eBay)")
    resultado2 = calcular_importacao(500, 100, loja_certificada=False)
    print(f"   Preço Produto: R$ {resultado2['preco_original_brl']}")
    print(f"   Frete: R$ {resultado2['frete_brl']}")
    print(f"   Impostos: R$ {resultado2['total_impostos_brl']}")
    print(f"   Taxa Real de Imposto: {resultado2['taxa_efetiva_porcentagem']}%")
    print(f"   TOTAL NA PORTA: R$ {resultado2['preco_final_brl']}")