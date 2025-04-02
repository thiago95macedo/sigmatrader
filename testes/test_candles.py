#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import csv
import logging
import os
import pandas as pd
import sys
import time
from datetime import datetime, timedelta

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iqoption.login import LoginIQOption
from iqoption.ativos import listar_ativos_abertos_com_payout

# Configuração de diretórios
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(TESTS_DIR, 'logs')
DATA_DIR = os.path.join(TESTS_DIR, 'dados')

# Criar diretórios se não existirem
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'test_candles.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestCandles')

def testar_conexao(email, senha):
    """Testa a conexão com a IQ Option e coleta velas"""
    logger.info("Iniciando teste de conexão com a IQ Option")
    
    # Conectar à IQ Option
    login_manager = LoginIQOption()
    conectado = login_manager.conectar(email, senha, "TREINAMENTO")
    
    if not conectado:
        logger.error(f"Falha na conexão: {getattr(login_manager, 'ultimo_erro', 'Motivo desconhecido')}")
        return False
    
    logger.info("Conexão bem-sucedida!")
    
    # Acesso a API
    api = login_manager.api
    
    # Verificar saldo
    saldo = api.get_balance()
    logger.info(f"Saldo da conta: {saldo}")
    
    # Testar obtenção de velas para diferentes ativos
    ativos = ["EURUSD", "EURJPY", "GBPUSD", "AUDUSD", "USDJPY"]
    
    for ativo in ativos:
        logger.info(f"Testando obtenção de velas para {ativo}")
        
        try:
            # Tenta obter 100 velas com timeframe de 1 minuto
            end_time = time.time()
            candles = api.get_candles(ativo, 60, 100, end_time)
            
            if candles and len(candles) > 0:
                logger.info(f"Sucesso! Obtidas {len(candles)} velas para {ativo}")
                
                # Exibe as primeiras 5 velas
                for i, candle in enumerate(candles[:5]):
                    logger.info(f"Vela {i+1}: Abertura: {candle['open']}, Fechamento: {candle['close']}, Tempo: {candle['from']}")
                
                # Salva os dados em um CSV para análise
                df = pd.DataFrame(candles)
                df.to_csv(os.path.join(DATA_DIR, f"{ativo}_candles.csv"), index=False)
                logger.info(f"Dados das velas de {ativo} salvos em {os.path.join(DATA_DIR, f'{ativo}_candles.csv')}")
            else:
                logger.error(f"Falha ao obter velas para {ativo}")
        
        except Exception as e:
            logger.error(f"Erro ao obter velas para {ativo}: {str(e)}")
    
    logger.info("Teste de obtenção de velas concluído")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Teste de coleta de velas da IQ Option')
    parser.add_argument('--email', help='Email de login', default="thiago95macedo@gmail.com")
    parser.add_argument('--senha', help='Senha de login', required=True)
    
    args = parser.parse_args()
    
    testar_conexao(args.email, args.senha) 