#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnóstico para verificar a obtenção de velas na aplicação SigmaTrader.
"""

import argparse
import json
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
from dependencias.iqoptionapi.iqoptionapi.stable_api import IQ_Option
from lstm.preprocessamento import obter_candles_historicos, criar_dataframe_com_indicadores

# Configuração de diretórios
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(TESTS_DIR, "logs")
DATA_DIR = os.path.join(TESTS_DIR, "dados")

# Criação de diretórios para resultados
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.StreamHandler(),
                       logging.FileHandler(os.path.join(LOGS_DIR, 'diagnostico_velas.log'))
                   ])
logger = logging.getLogger(__name__)

def diagnosticar_conexao(email, senha):
    """Testa a conexão com a IQ Option"""
    logger.info("=== INICIANDO DIAGNÓSTICO DE CONEXÃO ===")
    
    # Conectar à IQ Option
    login_manager = LoginIQOption()
    
    try:
        conectado = login_manager.conectar(email, senha, "TREINAMENTO")
        
        if not conectado:
            logger.error(f"FALHA NA CONEXÃO: {getattr(login_manager, 'ultimo_erro', 'Motivo desconhecido')}")
            return None
        
        logger.info("CONEXÃO BEM-SUCEDIDA!")
        
        # Informações da conta
        info = login_manager.obter_info_conta()
        logger.info(f"Tipo de conta: {info['tipo_conta']}")
        logger.info(f"Saldo: {info['saldo']} {info['moeda']}")
        
        # Verificar modo de conta usando acesso direto à API
        try:
            modo_direto = login_manager.api.get_balance_mode()
            logger.info(f"Modo de conta obtido diretamente da API: {modo_direto}")
        except Exception as e:
            logger.error(f"Erro ao obter modo direto: {e}")
            
        return login_manager
        
    except Exception as e:
        logger.error(f"ERRO DURANTE CONEXÃO: {e}", exc_info=True)
        return None

def diagnosticar_ativos(login_manager):
    """Testa a obtenção e listagem de ativos disponíveis"""
    logger.info("\n=== INICIANDO DIAGNÓSTICO DE ATIVOS ===")
    
    try:
        # Verificar ativos disponíveis em diferentes mercados
        for mercado in ["Binário/Turbo", "Digital", "Forex", "Cripto"]:
            logger.info(f"Testando listagem de ativos para mercado: {mercado}")
            ativos = listar_ativos_abertos_com_payout(login_manager.api, mercado)
            
            if ativos:
                logger.info(f"SUCESSO! Encontrados {len(ativos)} ativos para {mercado}")
                # Mostrar os 3 primeiros ativos como exemplo
                for i, (ativo, payload) in enumerate(ativos):
                    if i < 3:  # Limita a exibição a 3 ativos
                        logger.info(f"  - {ativo}: Payout {payload if payload is not None else 'N/A'}%")
            else:
                logger.warning(f"ATENÇÃO: Nenhum ativo encontrado para {mercado}")
                
        # Pegar um ativo para testes
        mercado_teste = "Binário/Turbo"  # Testamos com binários por padrão
        ativos_teste = listar_ativos_abertos_com_payout(login_manager.api, mercado_teste)
        
        if not ativos_teste:
            logger.error(f"FALHA: Nenhum ativo disponível para testar no mercado {mercado_teste}")
            return None
            
        # Seleciona o primeiro ativo da lista para teste
        ativo_teste = ativos_teste[0][0]
        logger.info(f"Ativo selecionado para testes de velas: {ativo_teste}")
        return ativo_teste
        
    except Exception as e:
        logger.error(f"ERRO DURANTE LISTAGEM DE ATIVOS: {e}", exc_info=True)
        return None

def diagnosticar_velas(login_manager, ativo):
    """Testa a obtenção de velas para um ativo"""
    logger.info(f"\n=== INICIANDO DIAGNÓSTICO DE VELAS PARA {ativo} ===")
    
    try:
        # Primeiro teste: Obtenção direta de velas via API
        logger.info("TESTE 1: Obtenção direta de velas via API")
        inicio = time.time()
        try:
            candles_direto = login_manager.api.get_candles(ativo, 60, 100, time.time())
            tempo_direto = time.time() - inicio
            
            if candles_direto and len(candles_direto) > 0:
                logger.info(f"SUCESSO! Obtidas {len(candles_direto)} velas diretamente da API em {tempo_direto:.2f}s")
                # Mostrar as 3 primeiras velas
                for i, candle in enumerate(candles_direto[:3]):
                    logger.info(f"  - Vela {i+1}: Abertura={candle['open']}, Fechamento={candle['close']}")
                
                # Salvar para análise
                with open(os.path.join(DATA_DIR, f"velas_direto_{ativo}.json"), 'w') as f:
                    json.dump(candles_direto, f, indent=2)
                logger.info(f"Velas salvas em {os.path.join(DATA_DIR, f'velas_direto_{ativo}.json')}")
            else:
                logger.error(f"FALHA! Nenhuma vela obtida diretamente da API")
        except Exception as e:
            logger.error(f"ERRO AO OBTER VELAS DIRETAMENTE: {e}", exc_info=True)
        
        # Segundo teste: Via função obter_candles_historicos
        logger.info("\nTESTE 2: Obtenção de velas via obter_candles_historicos")
        inicio = time.time()
        try:
            candles_funcao = obter_candles_historicos(login_manager.api, ativo, 100)
            tempo_funcao = time.time() - inicio
            
            if candles_funcao and len(candles_funcao) > 0:
                logger.info(f"SUCESSO! Obtidas {len(candles_funcao)} velas via função em {tempo_funcao:.2f}s")
                # Mostrar as 3 primeiras velas
                for i, candle in enumerate(candles_funcao[:3]):
                    logger.info(f"  - Vela {i+1}: Abertura={candle['open']}, Fechamento={candle['close']}")
                
                # Salvar para análise
                with open(os.path.join(DATA_DIR, f"velas_funcao_{ativo}.json"), 'w') as f:
                    json.dump(candles_funcao, f, indent=2)
                logger.info(f"Velas salvas em {os.path.join(DATA_DIR, f'velas_funcao_{ativo}.json')}")
            else:
                logger.error(f"FALHA! Nenhuma vela obtida via função obter_candles_historicos")
        except Exception as e:
            logger.error(f"ERRO AO OBTER VELAS VIA FUNÇÃO: {e}", exc_info=True)
        
        # Terceiro teste: Processamento completo com indicadores
        logger.info("\nTESTE 3: Processamento com criar_dataframe_com_indicadores")
        if candles_funcao and len(candles_funcao) > 0:
            try:
                inicio = time.time()
                df = criar_dataframe_com_indicadores(candles_funcao)
                tempo_df = time.time() - inicio
                
                if df is not None and len(df) > 0:
                    logger.info(f"SUCESSO! Criado DataFrame com {len(df)} linhas em {tempo_df:.2f}s")
                    logger.info(f"Colunas do DataFrame: {df.columns.tolist()}")
                    logger.info(f"Primeiras 3 linhas:\n{df.head(3)}")
                    
                    # Salvar para análise
                    df.to_csv(os.path.join(DATA_DIR, f"dataframe_{ativo}.csv"), index=True)
                    logger.info(f"DataFrame salvo em {os.path.join(DATA_DIR, f'dataframe_{ativo}.csv')}")
                else:
                    logger.error("FALHA! DataFrame vazio ou nulo após processamento")
            except Exception as e:
                logger.error(f"ERRO NO PROCESSAMENTO DO DATAFRAME: {e}", exc_info=True)
        else:
            logger.warning("Pulando teste de DataFrame pois não há velas para processar")
        
        return True
    except Exception as e:
        logger.error(f"ERRO GERAL NO DIAGNÓSTICO DE VELAS: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("=== DIAGNÓSTICO DO SISTEMA DE COLETA DE VELAS DO SIGMATRADER ===\n")
    
    # Solicita credenciais
    email = input("Email IQ Option: ").strip() or "thiago95macedo@gmail.com"
    senha = input("Senha IQ Option: ").strip()
    
    if not senha:
        print("Senha é obrigatória para prosseguir.")
        sys.exit(1)
    
    # Executa os diagnósticos em sequência
    login_manager = diagnosticar_conexao(email, senha)
    
    if login_manager:
        ativo_teste = diagnosticar_ativos(login_manager)
        
        if ativo_teste:
            diagnosticar_velas(login_manager, ativo_teste)
    
    print("\n=== DIAGNÓSTICO CONCLUÍDO ===")
    print(f"Verifique o arquivo de log em {os.path.join(LOGS_DIR, 'diagnostico_velas.log')}")
    print(f"Os dados coletados estão em {DATA_DIR}") 