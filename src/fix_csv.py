import pandas as pd
import os
import csv

# Caminho do arquivo
CSV_PATH = os.path.join('data', 'modelos_alvo.csv')

print(f"🚑 Tentando reparar o arquivo: {CSV_PATH}")

if os.path.exists(CSV_PATH):
    try:
        # 1. Lê ignorando as linhas quebradas (on_bad_lines='skip')
        df = pd.read_csv(CSV_PATH, on_bad_lines='skip')
        
        # 2. Salva forçando aspas em tudo (quoting=csv.QUOTE_NONNUMERIC)
        # Isso "blinda" o arquivo contra futuras vírgulas no texto
        df.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_NONNUMERIC)
        
        print(f"✅ Sucesso! Arquivo reparado. Total de modelos: {len(df)}")
        print("Agora você pode rodar o dashboard.py normalmente.")
        
    except Exception as e:
        print(f"❌ Erro crítico ao reparar: {e}")
else:
    print("⚠️ Arquivo não encontrado.")