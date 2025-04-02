## SigmaTrader com LSTM

Este sistema de trading automatizado foi desenvolvido para operar no mercado financeiro usando redes neurais LSTM (Long Short-Term Memory) com dados fornecidos pela IQOption. Ele é projetado para fazer previsões de preços e executar operações de compra e venda de forma automatizada, com capacidade de aprendizado contínuo e ajuste com base nos resultados das operações.

### Funcionalidades

#### Preprocessamento de Dados:
- O bot coleta dados de vários ativos financeiros e aplica uma série de transformações, incluindo normalização e cálculo de indicadores técnicos como médias móveis (MA), Índice de Força Relativa (RSI) e Estocástico (%K e %D).

#### Previsão com LSTM:
- Utiliza uma rede neural LSTM para fazer previsões baseadas em sequências de dados históricos. A arquitetura da rede é configurada para capturar padrões temporais e tendências de mercado.

#### Execução de Operações:
- Com base nas previsões, o bot executa operações de compra (CALL) ou venda (PUT) na IQOption. A execução é feita automaticamente, usando funções integradas para colocar apostas e verificar os resultados das operações.

#### Aprendizado Contínuo:
- O bot é projetado para aprender continuamente com os dados das operações. Ele armazena os resultados das operações e atualiza o modelo periodicamente, permitindo que ele se ajuste e melhore sua precisão ao longo do tempo.

### Estrutura do Código

O projeto está organizado da seguinte forma:

```
sigmatrader/
├── app.py                  # Aplicação principal com interface de usuário
├── __init__.py             # Inicialização do pacote
├── requirements.txt        # Dependências do projeto
├── README.md               # Documentação
├── configuracoes/          # Configurações personalizáveis
│   └── lstm_config.ini     # Parâmetros do modelo LSTM
├── data/                   # Módulo para gerenciamento de dados
│   ├── __init__.py
│   └── database.py         # Operações de banco de dados
├── iqoption/               # Módulo para interação com a IQ Option
│   └── ...
├── lstm/                   # Módulo de redes neurais LSTM
│   ├── __init__.py
│   ├── preprocessamento.py # Processamento e preparação dos dados
│   ├── treinamento.py      # Criação e treinamento de modelos
│   └── predicao.py         # Predição e execução de operações
├── log/                    # Arquivos de log
└── modelos/                # Modelos LSTM treinados
```

### Uso

#### Configuração Inicial:
1. Clone este repositório e instale as dependências necessárias:
   ```
   pip install -r requirements.txt
   ```
2. Configure suas credenciais da IQOption no sistema de gerenciamento de contas.

#### Treinamento do Modelo:
1. No menu principal, selecione "Treinar Modelo LSTM".
2. Escolha o ativo para treinar o modelo.
3. O sistema coletará dados históricos e treinará um modelo LSTM.

#### Execução do Bot:
1. No menu principal, selecione "Operação Automática LSTM".
2. Escolha o modelo treinado e o ativo para operar.
3. Configure o valor da operação e o número de operações a realizar.
4. O bot começará a analisar o mercado e executar operações com base nas previsões.

#### Análise de Predição:
1. No menu principal, selecione "Análise de Predição LSTM".
2. Escolha o modelo e o ativo para analisar.
3. O sistema fornecerá a previsão atual com nível de confiança e indicadores técnicos adicionais.

### Configurações Personalizáveis

No menu "Configurações LSTM", você pode ajustar os seguintes parâmetros:
- Tamanho da sequência (SEQ_LEN): Quantidade de períodos usados para fazer previsões
- Períodos futuros: Quantidade de períodos à frente para prever
- Tamanho do lote: Quantidade de amostras processadas em cada etapa de treinamento
- Épocas: Número de iterações completas pelos dados de treinamento
- Taxa de aprendizado: Taxa na qual o modelo se ajusta aos dados

### Requisitos
- Python 3.7 ou superior
- TensorFlow 2.4.0 ou superior
- Pandas, NumPy, scikit-learn
- Acesso à API da IQOption

### Contribuições
Sinta-se à vontade para contribuir com melhorias, correções de bugs ou novas funcionalidades. Abra uma issue ou envie um pull request com suas sugestões.
