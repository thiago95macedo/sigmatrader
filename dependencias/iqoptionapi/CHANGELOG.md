# Changelog

## [Não Versionado] - 2023-09-27

### Atualizado
- Atualizada a versão do websocket-client de 0.56.0 para 1.6.4
- Modificados os callbacks do websocket para compatibilidade com a nova versão
- Adicionado parâmetro `skip_utf8_validation=True` para melhorar a performance

### Corrigido
- Parâmetros nos métodos do WebsocketClient para compatibilidade com a nova API
- Assinatura do método `on_close` para receber os novos parâmetros (`close_status_code` e `close_msg`) 