#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo de login para a IQ Option API
"""

import logging
import time
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option

# Configuração de logging
logger = logging.getLogger(__name__)

# Constantes
TIPO_CONTA = {
    "REAL": "REAL",
    "TREINAMENTO": "PRACTICE",
    "TORNEIO": "TOURNAMENT"
}

class LoginIQOption:
    """Classe para gerenciar o login e seleção de conta na IQ Option"""
    
    def __init__(self):
        """Inicializa o gerenciador de login"""
        self.api = None
        self.email = None
        self.tipo_conta = None
        self.saldo = 0.0
        self.moeda = None
        self.conectado = False
    
    def conectar(self, email, senha, tipo_conta="TREINAMENTO"):
        """
        Realiza o login na IQ Option
        
        Parâmetros:
            email (str): Email da conta
            senha (str): Senha da conta
            tipo_conta (str): REAL, TREINAMENTO ou TORNEIO
            
        Retorna:
            bool: True se o login foi bem-sucedido, False caso contrário
        """
        logger.info(f"Iniciando conexão com a IQ Option para o email: {email}")
        
        # Normaliza o tipo de conta
        if tipo_conta not in TIPO_CONTA:
            logger.warning(f"Tipo de conta desconhecido: {tipo_conta}. Usando conta de TREINAMENTO.")
            tipo_conta = "TREINAMENTO"
        
        # Inicializa a conexão
        self.api = IQ_Option(email, senha)
        
        # Tenta conectar
        status, motivo = self.api.connect()
        
        if status:
            logger.info("Conexão estabelecida com sucesso!")
            self.email = email
            self.conectado = True
            
            # Altera para o tipo de conta desejado
            self._selecionar_tipo_conta(tipo_conta)
            
            # Obtém informações da conta
            self._atualizar_saldo()
            
            return True
        else:
            logger.error(f"Falha na conexão: {motivo}")
            self.conectado = False
            return False
    
    def _selecionar_tipo_conta(self, tipo_conta):
        """
        Seleciona o tipo de conta a ser usada
        
        Parâmetros:
            tipo_conta (str): REAL, TREINAMENTO ou TORNEIO
        
        Retorna:
            bool: True se a mudança foi bem-sucedida, False caso contrário
        """
        if not self.conectado or not self.api:
            logger.error("Não é possível selecionar tipo de conta sem estar conectado")
            return False
        
        # Obtém o código do tipo de conta da API
        codigo_tipo = TIPO_CONTA.get(tipo_conta, "PRACTICE")
        
        # Seleciona o tipo de conta
        logger.info(f"Alterando para conta do tipo: {tipo_conta}")
        resultado = self.api.change_balance(codigo_tipo)
        
        if resultado:
            self.tipo_conta = tipo_conta
            logger.info(f"Tipo de conta alterado para: {tipo_conta}")
            
            # Atualiza saldo após a mudança de conta
            self._atualizar_saldo()
            return True
        else:
            logger.error(f"Falha ao alterar para o tipo de conta: {tipo_conta}")
            return False
    
    def _atualizar_saldo(self):
        """
        Atualiza as informações de saldo da conta
        
        Retorna:
            float: Saldo atual da conta
        """
        if not self.conectado or not self.api:
            logger.error("Não é possível obter saldo sem estar conectado")
            return 0.0
        
        try:
            # Obtém o saldo e a moeda
            self.saldo = self.api.get_balance()
            self.moeda = self.api.get_currency()
            
            logger.info(f"Saldo atual: {self.saldo} {self.moeda}")
            return self.saldo
        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            return 0.0
    
    def verificar_conexao(self):
        """
        Verifica se a conexão com a API está ativa
        
        Retorna:
            bool: True se está conectado, False caso contrário
        """
        if not self.api:
            return False
        
        return self.api.check_connect()
    
    def obter_info_conta(self):
        """
        Retorna as informações atuais da conta
        
        Retorna:
            dict: Dicionário com informações da conta
        """
        return {
            "email": self.email,
            "tipo_conta": self.tipo_conta,
            "saldo": self.saldo,
            "moeda": self.moeda,
            "conectado": self.conectado,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Função auxiliar para uso direto do módulo
def fazer_login(email, senha, tipo_conta="TREINAMENTO"):
    """
    Função auxiliar para realizar login na IQ Option
    
    Parâmetros:
        email (str): Email da conta
        senha (str): Senha da conta
        tipo_conta (str): REAL, TREINAMENTO ou TORNEIO
    
    Retorna:
        tuple: (LoginIQOption, bool) - Objeto de login e status da conexão
    """
    login_manager = LoginIQOption()
    status = login_manager.conectar(email, senha, tipo_conta)
    
    return login_manager, status 