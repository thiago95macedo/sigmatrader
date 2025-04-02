# Testes do SigmaTrader

Este diretório contém scripts para testar diferentes funcionalidades do SigmaTrader.

## Estrutura

- `logs/` - Diretório para armazenar arquivos de log gerados pelos testes
- `dados/` - Diretório para armazenar dados coletados durante os testes

## Scripts Disponíveis

### 1. Diagnóstico de Velas (`diagnostico_velas.py`)

Script para diagnóstico completo da funcionalidade de coleta de velas do SigmaTrader.

```bash
python diagnostico_velas.py
```

Este script verifica:
- Conexão com a IQ Option
- Listagem de ativos disponíveis
- Obtenção direta de velas via API
- Funcionamento da função `obter_candles_historicos`
- Processamento de velas com a função `criar_dataframe_com_indicadores`

### 2. Teste de Coleta de Velas (`test_candles.py`)

Script para testar especificamente a coleta de velas para um conjunto de ativos.

```bash
python test_candles.py --senha "sua_senha"
```

Parâmetros:
- `--email` - Email de login (opcional, padrão: thiago95macedo@gmail.com)
- `--senha` - Senha de login (obrigatório)

### 3. Teste de GPU (`test_gpu.py`)

Script para verificar se o TensorFlow está reconhecendo e utilizando a GPU corretamente.

```bash
python test_gpu.py
```

Este script realiza operações tensoriais na CPU e GPU e compara o desempenho entre elas.

### 4. Teste de GPU Simplificado (`test_gpu_simple.py`)

Versão simplificada do teste de GPU para verificação rápida.

```bash
python test_gpu_simple.py
```

Este script verifica se a GPU está disponível para o TensorFlow e realiza um teste simples de multiplicação de matrizes.

### 5. Teste Simples de Velas (`teste_simples_velas.py`)

Versão simplificada para testar apenas a coleta de velas para um conjunto específico de ativos.

```bash
python teste_simples_velas.py
```

Este script testa a conexão com a IQ Option e tenta obter velas para os principais pares de moedas, salvando os resultados em formato JSON.

## Como Adicionar Novos Testes

1. Crie um novo script de teste no diretório `testes/`
2. Use as constantes `TESTS_DIR`, `LOGS_DIR` e `DATA_DIR` para organizar os resultados
3. Atualize este README com informações sobre o novo teste 