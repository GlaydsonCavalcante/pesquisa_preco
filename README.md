# pesquisa_preco
Pesquisa de Preço de itens novos e usados com base em um CSV com dados e acaliações

piano_scout/
│
├── data/                      # A "Memória" do projeto
│   ├── modelos_alvo.csv       # O ficheiro que tu controlas (teus scores)
│   └── historico_precos.db    # O banco de dados SQL (automático)
│
├── src/                       # O "Cérebro" (Código Fonte)
│   ├── __init__.py            # (Arquivo vazio para o Python reconhecer a pasta)
│   ├── config.py              # Configurações (URLs, cabeçalhos, filtros)
│   ├── database.py            # Gere o SQL (salvar, ler histórico)
│   ├── scraper.py             # O "Caçador" (vai à web buscar dados)
│   └── analyzer.py            # O "Juiz" (aplica filtros de Brasília e calcula notas)
│
├── main.py                    # O "Chefe" (executa o fluxo completo)
├── requirements.txt           # Lista de ferramentas necessárias (bibliotecas)
└── README.md                  # Instruções de uso (para tu te lembrares no futuro)