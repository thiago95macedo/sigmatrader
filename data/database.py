#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para gerenciamento do banco de dados SQLite do SigmaTrader
"""

import os
import sqlite3
import logging
from datetime import datetime

# Import necessário para type hinting, se aplicável
# from ..iqoption.login import LoginIQOption

# Configuração de logging
logger = logging.getLogger(__name__)

# Constantes do Banco de Dados
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "sigmatrader.db")

def _get_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_PATH)

def _execute_query(query, params=(), fetch=None, commit=False):
    """
    Executa uma consulta SQL genérica.
    
    Args:
        query (str): A consulta SQL a ser executada.
        params (tuple): Parâmetros para a consulta.
        fetch (str, optional): 'one' para fetchone(), 'all' para fetchall(). 
                             Defaults to None.
        commit (bool, optional): True para confirmar a transação (INSERT, UPDATE, DELETE).
                                 Defaults to False.
                                 
    Returns:
        Variado: Resultado(s) da consulta se fetch for especificado, 
                 Boolean (True para sucesso, False para falha) se commit=True, 
                 None em caso de erro.
    """
    conn = None
    result = None
    success = False
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == 'one':
            result = cursor.fetchone()
            success = True
        elif fetch == 'all':
            result = cursor.fetchall()
            success = True
        elif commit:
            conn.commit()
            # Pode retornar rowcount se for útil, mas True/False é mais simples
            success = True 
        else:
            # Para casos onde apenas executamos (ex: CREATE TABLE)
            success = True
            
    except sqlite3.Error as e:
        logger.error(f"Erro ao executar query: {query} - Params: {params} - Erro: {e}")
        success = False # Garante que o erro retorne False ou None
        result = None   # Garante que o erro não retorne dados parciais
    finally:
        if conn:
            conn.close()
            
    # Decide o que retornar baseado na operação
    if fetch:
        return result # Retorna dados (ou None em caso de erro/sem dados)
    else:
        return success # Retorna True/False para commit ou execução simples

def _add_column_if_not_exists(table_name, column_info):
    """Verifica e adiciona uma coluna a uma tabela se ela não existir."""
    # Precisa de uma conexão separada ou passar o cursor
    conn = None
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        column_name = column_info["name"]
        column_def = column_info["definition"]
        
        cursor.execute(f"PRAGMA table_info({table_name});")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if column_name not in existing_columns:
            logger.info(f"Adicionando coluna '{column_name}' à tabela '{table_name}'...")
            # Executa o ALTER TABLE
            alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};"
            cursor.execute(alter_query)
            conn.commit() # Precisa commitar o ALTER TABLE
            logger.info(f"Coluna '{column_name}' adicionada com sucesso.")
            
    except sqlite3.Error as e:
        logger.error(f"Falha ao adicionar/verificar coluna '{column_name}' na tabela '{table_name}': {e}")
    finally:
        if conn:
            conn.close()

def inicializar_banco_dados():
    """
    Garante que o diretório, o banco de dados e as tabelas existam.
    Também adiciona colunas faltantes (migração simples).
    """
    logger.info("Inicializando e verificando banco de dados...")
    
    # 1. Garante o diretório
    if not os.path.exists(DB_DIR):
        logger.info(f"Criando diretório {DB_DIR}")
        os.makedirs(DB_DIR)
    
    try:
        # 2. Cria tabelas base se não existirem (usando _execute_query)
        logger.info("Verificando/Criando tabelas base...")
        _execute_query('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY,
            chave TEXT UNIQUE NOT NULL,
            valor TEXT NOT NULL,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        _execute_query('''
        CREATE TABLE IF NOT EXISTS contas_iqoption (
            id INTEGER PRIMARY KEY,
            nome_completo TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
        ''')
        
        _execute_query('''
        CREATE TABLE IF NOT EXISTS operacoes (
            id INTEGER PRIMARY KEY,
            conta_id INTEGER NOT NULL,
            ativo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            direcao TEXT NOT NULL,
            valor REAL NOT NULL,
            resultado REAL,
            data_entrada TIMESTAMP,
            data_saida TIMESTAMP,
            status TEXT DEFAULT 'aberta',
            FOREIGN KEY (conta_id) REFERENCES contas_iqoption(id)
        )
        ''')
        
        _execute_query('''
        CREATE TABLE IF NOT EXISTS historico_ativos (
            id INTEGER PRIMARY KEY,
            ativo TEXT NOT NULL,
            abertura REAL NOT NULL,
            fechamento REAL NOT NULL,
            maxima REAL NOT NULL,
            minima REAL NOT NULL,
            timestamp TIMESTAMP,
            timeframe TEXT NOT NULL
        )
        ''')
        
        # 3. Verifica e adiciona colunas faltantes (Migração Simples)
        logger.info("Verificando/Aplicando migrações de colunas...")
        colunas_contas = [
            {"name": "tipo_conta", "definition": "TEXT DEFAULT 'TREINAMENTO'"},
            {"name": "data_cadastro", "definition": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"},
            {"name": "ultimo_acesso", "definition": "TIMESTAMP"},
            {"name": "saldo_real", "definition": "REAL DEFAULT 0.0"},
            {"name": "saldo_treinamento", "definition": "REAL DEFAULT 0.0"},
            {"name": "saldo_torneio", "definition": "REAL DEFAULT 0.0"},
            {"name": "moeda", "definition": "TEXT DEFAULT 'USD'"},
            {"name": "ultima_atualizacao_saldo", "definition": "TIMESTAMP"},
            {"name": "ativo", "definition": "BOOLEAN DEFAULT 1"},
            {"name": "iq_user_id", "definition": "INTEGER"},
            {"name": "iq_name", "definition": "TEXT"},
            {"name": "iq_nickname", "definition": "TEXT"},
            {"name": "iq_avatar_url", "definition": "TEXT"},
        ]
        for col_info in colunas_contas:
            _add_column_if_not_exists("contas_iqoption", col_info)
            
        # Adicione verificações para outras tabelas aqui se necessário

        # 4. Verifica configurações iniciais
        config_existente = _execute_query("SELECT valor FROM configuracoes WHERE chave = 'data_criacao'", fetch='one')
        if not config_existente:
            logger.info("Inserindo configurações iniciais...")
            _execute_query('''
            INSERT INTO configuracoes (chave, valor) VALUES 
            ('versao', '1.0.0'),
            ('data_criacao', ?)
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),), commit=True)
        
        logger.info("Inicialização/Verificação do banco de dados concluída com sucesso!")
        return True
        
    except Exception as e: # Captura qualquer erro durante a inicialização
        logger.error(f"Erro fatal durante a inicialização/verificação do banco de dados: {e}", exc_info=True)
        return False

def verificar_contas_existentes():
    """
    Verifica se existem contas IQ Option ativas cadastradas.
    Retorna o número de contas encontradas.
    """
    query = "SELECT COUNT(*) FROM contas_iqoption WHERE ativo = 1"
    result = _execute_query(query, fetch='one')
    return result[0] if result else 0

def listar_contas():
    """
    Lista todas as contas IQ Option ativas.
    Retorna uma lista de tuplas (id, nome, email, tipo_conta).
    """
    query = "SELECT id, nome_completo, email, tipo_conta FROM contas_iqoption WHERE ativo = 1 ORDER BY nome_completo"
    result = _execute_query(query, fetch='all')
    return result if result else []

def verificar_email_existente(email):
    """
    Verifica se um email já está cadastrado (ativo ou inativo).
    Retorna True se o email existe, False caso contrário.
    """
    query = "SELECT id FROM contas_iqoption WHERE email = ?"
    result = _execute_query(query, (email,), fetch='one')
    return result is not None

def cadastrar_conta_db(nome_completo, email, senha, tipo_conta):
    """
    Cadastra uma nova conta IQ Option no banco de dados.
    """
    query = """
    INSERT INTO contas_iqoption (nome_completo, email, senha, tipo_conta)
    VALUES (?, ?, ?, ?)
    """
    success = _execute_query(query, (nome_completo, email, senha, tipo_conta), commit=True)
    if success:
        logger.info(f"Nova conta cadastrada para o email {email}")
    return success

def obter_detalhes_conta(conta_id):
    """
    Obtém os detalhes de uma conta ativa específica.
    Retorna uma tupla (id, nome, email, senha, tipo_conta) ou None.
    """
    query = "SELECT id, nome_completo, email, senha, tipo_conta FROM contas_iqoption WHERE id = ? AND ativo = 1"
    result = _execute_query(query, (conta_id,), fetch='one')
    return result

def obter_nome_conta(conta_id):
    """
    Obtém o nome completo de uma conta ativa específica.
    Retorna o nome ou None se a conta não for encontrada.
    """
    query = "SELECT nome_completo FROM contas_iqoption WHERE id = ? AND ativo = 1"
    result = _execute_query(query, (conta_id,), fetch='one')
    return result[0] if result else None

def deletar_conta_db(conta_id):
    """
    Marca uma conta como inativa (soft delete) no banco de dados.
    Retorna True se sucesso, False caso contrário.
    """
    # Verifica se a conta existe antes de tentar deletar (opcional, mas bom)
    # if not obter_nome_conta(conta_id):
    #     logger.warning(f"Tentativa de deletar conta inexistente: {conta_id}")
    #     return False
        
    query = "UPDATE contas_iqoption SET ativo = 0 WHERE id = ? AND ativo = 1"
    success = _execute_query(query, (conta_id,), commit=True)
    # Aqui _execute_query retorna True/False para commit
    if success:
        # Poderíamos verificar cursor.rowcount se _execute_query retornasse o cursor
        logger.info(f"Conta {conta_id} marcada como inativa")
        # Nota: O log acima pode ser impreciso se a conta já estava inativa, 
        # mas a operação em si não falhou. Para precisão, precisaríamos do rowcount.
    # else: # O erro já foi logado por _execute_query
        # logger.warning(f"Falha ao marcar conta {conta_id} como inativa.")
        
    return success # Retorna o status da execução da query

def registrar_acesso(conta_id):
    """
    Registra o último acesso de uma conta no banco de dados.
    """
    query = "UPDATE contas_iqoption SET ultimo_acesso = ? WHERE id = ? AND ativo = 1"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = _execute_query(query, (now, conta_id), commit=True)
    if success:
        logger.info(f"Acesso registrado para conta {conta_id}")
    return success

def obter_saldos_conta(conta_id):
    """
    Obtém os saldos armazenados de uma conta ativa.
    Retorna: dict com saldos ou None.
    """
    query = """
    SELECT saldo_real, saldo_treinamento, saldo_torneio, 
           moeda, ultima_atualizacao_saldo
    FROM contas_iqoption 
    WHERE id = ? AND ativo = 1
    """
    result = _execute_query(query, (conta_id,), fetch='one')
    if result:
        return {
            "saldo_real": result[0],
            "saldo_treinamento": result[1],
            "saldo_torneio": result[2],
            "moeda": result[3],
            "ultima_atualizacao": result[4]
        }
    return None

def atualizar_saldos_conta(conta_id, tipo_atual, saldo_atual, moeda):
    """
    Atualiza o saldo do tipo de conta especificado no banco de dados.
    Mantém os saldos dos outros tipos de conta.
    Retorna: bool indicando sucesso.
    """
    try:
        # Garante que os valores são válidos
        saldo_atual = saldo_atual if saldo_atual is not None else 0.0
        moeda = moeda or "USD"
        tipo_atual = tipo_atual.upper() if tipo_atual else "TREINAMENTO"
        
        # Obtém os saldos anteriores
        saldos_anteriores = obter_saldos_conta(conta_id)
        if not saldos_anteriores:
            logger.warning(f"Tentativa de atualizar saldo para conta inativa ou inexistente: {conta_id}")
            return False

        # Define os valores a serem atualizados
        saldo_real = saldos_anteriores.get("saldo_real", 0.0)
        saldo_treinamento = saldos_anteriores.get("saldo_treinamento", 0.0)
        saldo_torneio = saldos_anteriores.get("saldo_torneio", 0.0)
        # Usa get com default para mais segurança
        
        # Atualiza o saldo correto com base no tipo_atual
        if tipo_atual == "REAL":
            saldo_real = saldo_atual
        elif tipo_atual == "TREINAMENTO":
            saldo_treinamento = saldo_atual
        elif tipo_atual == "TORNEIO":
            saldo_torneio = saldo_atual
        else:
            logger.warning(f"Tipo de conta desconhecido '{tipo_atual}' ao atualizar saldo. Usando TREINAMENTO.")
            saldo_treinamento = saldo_atual # Ou poderia retornar erro

        # Atualiza no banco de dados usando _execute_query
        query = """
        UPDATE contas_iqoption 
        SET saldo_real = ?,
            saldo_treinamento = ?,
            saldo_torneio = ?,
            moeda = ?,
            ultima_atualizacao_saldo = ?
        WHERE id = ? AND ativo = 1
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            round(saldo_real, 2), # Arredonda para 2 casas decimais
            round(saldo_treinamento, 2),
            round(saldo_torneio, 2),
            moeda,
            now,
            conta_id
        )
        
        success = _execute_query(query, params, commit=True)
        if success:
            logger.info(f"Saldo {tipo_atual} atualizado para conta {conta_id}")
        # else: O erro já foi logado
            
        return success
        
    except Exception as e:
        logger.error(f"Erro ao preparar atualização do saldo {tipo_atual} da conta {conta_id}: {e}", exc_info=True)
        return False

def obter_id_conta_atual(email):
    """
    Obtém o ID da conta ativa pelo email.
    Retorna: int ID da conta ou None.
    """
    query = "SELECT id FROM contas_iqoption WHERE email = ? AND ativo = 1"
    result = _execute_query(query, (email,), fetch='one')
    return result[0] if result else None

def obter_perfil_conta_local(conta_id):
    """
    Obtém os dados de perfil IQ Option armazenados localmente para uma conta.
    
    Args:
        conta_id (int): O ID da conta no banco de dados local.
        
    Returns:
        dict: Um dicionário com as chaves 'iq_user_id', 'iq_name', 'iq_nickname', 
              'iq_avatar_url' ou None se a conta não for encontrada ou não tiver dados.
    """
    query = """
    SELECT iq_user_id, iq_name, iq_nickname, iq_avatar_url
    FROM contas_iqoption
    WHERE id = ? AND ativo = 1
    """
    result = _execute_query(query, (conta_id,), fetch='one')
    
    if result:
        return {
            "iq_user_id": result[0],
            "iq_name": result[1],
            "iq_nickname": result[2],
            "iq_avatar_url": result[3]
        }
    else:
        logger.warning(f"Nenhum dado de perfil local encontrado para conta ID {conta_id}")
        return None

def atualizar_perfil_conta_iq(conta_id, perfil_data):
    """
    Atualiza os dados do perfil IQ Option (user_id, nome, nickname, avatar) 
    para uma conta específica no banco de dados local.

    Args:
        conta_id (int): O ID da conta no banco de dados local.
        perfil_data (dict): Um dicionário contendo os dados do perfil obtidos da API. 
                            Esperam-se chaves como 'user_id', 'name', 'nickname', 'avatar'.
                            Serão usados os valores encontrados, ignorando chaves ausentes.
    
    Returns:
        bool: True se a atualização foi bem-sucedida, False caso contrário.
    """
    campos_para_atualizar = []
    valores_para_atualizar = []

    # Mapeia chaves do dicionário para nomes de coluna e adiciona se presente
    mapeamento = {
        'user_id': 'iq_user_id',
        'name': 'iq_name',
        'nickname': 'iq_nickname',
        'avatar': 'iq_avatar_url' # Assumindo que a API retorna 'avatar' para a URL
    }

    for chave_api, coluna_db in mapeamento.items():
        if chave_api in perfil_data and perfil_data[chave_api] is not None:
            campos_para_atualizar.append(f"{coluna_db} = ?")
            valores_para_atualizar.append(perfil_data[chave_api])

    if not campos_para_atualizar:
        logger.warning(f"Nenhum dado de perfil válido encontrado para atualizar conta ID {conta_id}.")
        return False # Nada para atualizar

    # Adiciona o conta_id ao final da lista de valores para o WHERE
    valores_para_atualizar.append(conta_id)

    query = f"""
    UPDATE contas_iqoption 
    SET {', '.join(campos_para_atualizar)}
    WHERE id = ?
    """
    
    success = _execute_query(query, tuple(valores_para_atualizar), commit=True)
    
    if success:
        logger.info(f"Perfil IQ Option atualizado no DB para conta ID {conta_id}.")
    else:
        logger.error(f"Falha ao atualizar perfil IQ Option no DB para conta ID {conta_id}.")
        
    return success 