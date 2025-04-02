#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import logging
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iqoption.login import LoginIQOption

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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'teste_simples_velas.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TesteVelas')

# Lista de ativos para testar
ATIVOS_TESTE = [
    "EURUSD",
    "EURGBP",
    "EURJPY",
    "GBPUSD",
    "AUDUSD"
]

def testar_coleta_velas(email, senha):
    """Função para testar a coleta de velas diretamente da API"""
    logger.info("=== INICIANDO TESTE SIMPLES DE COLETA DE VELAS ===")
    
    # Conectar à IQ Option
    login_manager = LoginIQOption()
    
    try:
        conectado = login_manager.conectar(email, senha, "TREINAMENTO")
        
        if not conectado:
            logger.error(f"FALHA NA CONEXÃO: {getattr(login_manager, 'ultimo_erro', 'Motivo desconhecido')}")
            return False
        
        logger.info("CONEXÃO BEM-SUCEDIDA!")
        
        # Informações da conta
        info = login_manager.obter_info_conta()
        logger.info(f"Tipo de conta: {info['tipo_conta']}")
        logger.info(f"Saldo: {info['saldo']} {info['moeda']}")
        
        # API direta
        api = login_manager.api
        
        # Testar cada ativo
        resultados = {}
        
        for ativo in ATIVOS_TESTE:
            logger.info(f"Testando coleta de velas para {ativo}")
            
            try:
                # Tenta obter velas
                start_time = time.time()
                candles = api.get_candles(ativo, 60, 20, time.time())
                end_time = time.time()
                
                if candles and len(candles) > 0:
                    logger.info(f"✓ SUCESSO: Obtidas {len(candles)} velas para {ativo} em {end_time - start_time:.2f}s")
                    
                    # Salvar primeira vela para verificação
                    primeira_vela = candles[0]
                    logger.info(f"   Primeira vela: Abertura={primeira_vela['open']}, Fechamento={primeira_vela['close']}")
                    
                    # Salvar velas em arquivo
                    arquivo_velas = os.path.join(DATA_DIR, f"{ativo}_velas.json")
                    with open(arquivo_velas, 'w') as f:
                        json.dump(candles, f, indent=2)
                    
                    logger.info(f"   Velas salvas em {arquivo_velas}")
                    resultados[ativo] = True
                else:
                    logger.error(f"✗ FALHA: Não foi possível obter velas para {ativo}")
                    resultados[ativo] = False
            
            except Exception as e:
                logger.error(f"✗ ERRO ao coletar velas para {ativo}: {str(e)}")
                resultados[ativo] = False
        
        # Resumo final
        sucessos = sum(1 for v in resultados.values() if v)
        logger.info("\n=== RESUMO ===")
        logger.info(f"Total de ativos testados: {len(ATIVOS_TESTE)}")
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Falhas: {len(ATIVOS_TESTE) - sucessos}")
        
        for ativo, sucesso in resultados.items():
            logger.info(f"{ativo}: {'✓' if sucesso else '✗'}")
        
        return True
    
    except Exception as e:
        logger.error(f"ERRO DURANTE TESTE: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== TESTE SIMPLES DE COLETA DE VELAS DO SIGMATRADER ===\n")
    
    # Solicita credenciais
    email = input("Email IQ Option: ").strip() or "thiago95macedo@gmail.com"
    senha = input("Senha IQ Option: ").strip()
    
    if not senha:
        print("Senha é obrigatória para prosseguir.")
        sys.exit(1)
    
    testar_coleta_velas(email, senha)
    
    print("\n=== TESTE CONCLUÍDO ===")
    print(f"Verifique o arquivo de log em {os.path.join(LOGS_DIR, 'teste_simples_velas.log')}")
    print(f"Os dados coletados estão em {DATA_DIR}") 