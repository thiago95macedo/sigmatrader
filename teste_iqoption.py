#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de teste completo para verificar a conexão com a IQ Option API
"""

import sys
import logging
import time
import json
from datetime import datetime
from dependencias.iqoptionapi.iqoptionapi.stable_api import IQ_Option

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("teste_iqoption.log"),
        logging.StreamHandler()
    ]
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
    
    # Fase 1: Conexão
    print("\n[FASE 1] Estabelecendo conexão WebSocket...")
    conexao_start = time.time()
    status, motivo = api.connect()
    conexao_time = time.time() - conexao_start
    
    if not status:
        print(f"❌ Falha na conexão: {motivo}")
        return False, conexao_time
    
    print(f"✅ Conexão bem-sucedida! ({conexao_time:.2f}s)")
    print(f"Timestamp do servidor: {api.get_server_timestamp()}")
    
    # Fase 2: Verificar tipo de conta
    print("\n[FASE 2] Verificando tipo de conta...")
    try:
        conta_tipo = api.get_balance_mode()
        print(f"✅ Tipo de conta atual: {conta_tipo}")
        
        # Obter saldo
        saldo = api.get_balance()
        moeda = api.get_currency()
        print(f"✅ Saldo atual: {saldo} {moeda}")
    except Exception as e:
        print(f"❌ Erro ao obter informações da conta: {e}")
        return False, conexao_time
    
    # Fase 3: Testar mudança de tipo de conta
    print("\n[FASE 3] Testando mudança de tipo de conta...")
    try:
        novo_tipo = "PRACTICE" if conta_tipo != "PRACTICE" else "TOURNAMENT"
        print(f"Tentando mudar para conta {novo_tipo}")
        api.change_balance(novo_tipo)
        
        # Verificar mudança
        novo_tipo_atual = api.get_balance_mode()
        if novo_tipo == novo_tipo_atual:
            print(f"✅ Mudança de conta bem-sucedida: {novo_tipo_atual}")
        else:
            print(f"⚠️ Conta atual após tentativa de mudança: {novo_tipo_atual}")
    except Exception as e:
        print(f"❌ Erro ao tentar mudar tipo de conta: {e}")
    
    # Fase 4: Obter ativos disponíveis
    print("\n[FASE 4] Obtendo ativos disponíveis...")
    try:
        ativos_binarios = api.get_all_open_time()
        if ativos_binarios:
            count_open = 0
            for tipo, ativos in ativos_binarios.items():
                for ativo, info in ativos.items():
                    if info.get('open', False):
                        count_open += 1
            
            print(f"✅ {count_open} ativos abertos encontrados")
        else:
            print("⚠️ Nenhum ativo encontrado ou retorno vazio")
    except Exception as e:
        print(f"❌ Erro ao obter ativos disponíveis: {e}")
    
    # Desconectar
    print("\n[FASE 5] Finalizando teste...")
    try:
        api.logout()
        print("✅ Desconectado com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao desconectar: {e}")
    
    return True, conexao_time

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" TESTE DE CONEXÃO COM IQ OPTION API ".center(50, "="))
    print("="*50 + "\n")
    
    if len(sys.argv) < 3:
        print("Uso: python teste_iqoption.py <email> <senha>")
        sys.exit(1)
    
    email = sys.argv[1]
    senha = sys.argv[2]
    
    start_time = time.time()
    sucesso, tempo_conexao = testar_conexao(email, senha)
    tempo_total = time.time() - start_time
    
    print("\n" + "-"*50)
    print(f"Tempo de conexão: {tempo_conexao:.2f} segundos")
    print(f"Tempo total de execução: {tempo_total:.2f} segundos")
    print("-"*50)
    
    if sucesso:
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!\n")
        sys.exit(0)
    else:
        print("\n❌ TESTE FALHOU!\n")
        sys.exit(1) 