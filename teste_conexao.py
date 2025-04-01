#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de teste para a conexão com a IQ Option API
"""

import sys
import logging
import time
from dependencias.iqoptionapi.iqoptionapi.stable_api import IQ_Option

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silencia logs de bibliotecas de terceiros
logging.getLogger('iqoptionapi.ws.client').setLevel(logging.WARNING)
logging.getLogger('websocket').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

def testar_conexao(email, senha):
    """
    Testa a conexão com a IQ Option API
    """
    print(f"Tentando conectar à IQ Option com o email: {email}")
    print("Inicializando API...")
    
    api = IQ_Option(email, senha)
    
    print("Estabelecendo conexão WebSocket...")
    status, motivo = api.connect()
    
    if status:
        print(f"Conexão bem-sucedida!")
        print(f"Timestamp do servidor: {api.get_server_timestamp()}")
        
        # Verificar o tipo de conta
        conta_tipo = api.get_balance_mode()
        print(f"Tipo de conta atual: {conta_tipo}")
        
        # Obter saldo
        saldo = api.get_balance()
        moeda = api.get_currency()
        print(f"Saldo atual: {saldo} {moeda}")
        
        # Desconectar
        print("Desconectando...")
        api.logout()
        print("Desconectado com sucesso!")
        return True
    else:
        print(f"Falha na conexão: {motivo}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python teste_conexao.py <email> <senha>")
        sys.exit(1)
    
    email = sys.argv[1]
    senha = sys.argv[2]
    
    start_time = time.time()
    sucesso = testar_conexao(email, senha)
    tempo_total = time.time() - start_time
    
    print(f"\nTempo total de execução: {tempo_total:.2f} segundos")
    
    if sucesso:
        print("✅ Teste concluído com sucesso!")
        sys.exit(0)
    else:
        print("❌ Teste falhou!")
        sys.exit(1) 