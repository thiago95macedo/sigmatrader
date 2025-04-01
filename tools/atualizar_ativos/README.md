# SigmaTrader - IQ Option API

## Atualização de Ativos

Este projeto utiliza a API não oficial da IQ Option para operações de trading automatizado.

### Script de Atualização de Ativos

O arquivo `atualizar_ativos.py` foi criado para obter os códigos de ativos mais recentes diretamente da plataforma IQ Option. Esse script:

1. Conecta-se à API da IQ Option usando suas credenciais
2. Obtém a lista de todos os ativos disponíveis atualmente
3. Extrai os IDs correspondentes a cada ativo
4. Gera um arquivo JSON com os dados obtidos
5. Cria um arquivo `constants_atualizado.py` que pode substituir o arquivo `constants.py` existente

### Como usar o script de atualização

1. Edite o arquivo `atualizar_ativos.py` e substitua as variáveis:
   - `EMAIL` com seu email de login na IQ Option
   - `SENHA` com sua senha de login na IQ Option

2. Execute o script:
   ```bash
   python atualizar_ativos.py
   ```

3. Após a execução bem-sucedida, você encontrará:
   - Um arquivo JSON contendo todos os ativos e seus IDs (exemplo: `ativos_iqoption_20250331.json`)
   - Um arquivo `constants_atualizado.py` que pode substituir o arquivo `constants.py` na pasta `dependencias/iqoptionapi/iqoptionapi/`

4. Para atualizar o arquivo constants.py:
   ```bash
   cp constants_atualizado.py dependencias/iqoptionapi/iqoptionapi/constants.py
   ```

### Observações

- A atualização dos códigos de ativos é importante porque a plataforma IQ Option pode adicionar, remover ou modificar ativos e seus IDs ao longo do tempo
- Recomenda-se executar este script periodicamente para manter a lista de ativos atualizada
- Em caso de falha na autenticação, verifique suas credenciais e a disponibilidade da API

### Aviso Legal

Este projeto utiliza uma API não oficial. Use por sua conta e risco, respeitando os termos de serviço da IQ Option. 