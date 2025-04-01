#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo de login para a IQ Option API
"""

import logging
import time
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option
from data import atualizar_perfil_conta_iq # Importa a nova função

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
        """
        Inicializa o gerenciador de login
        """
        self.api = None
        self.email = None
        self.conectado = False
        self.tipo_conta = None
        self.saldo = 0.0
        self.moeda = None
        self.ultimo_erro = None # Para armazenar a última mensagem de erro
    
    def conectar(self, email, senha, tipo_conta="TREINAMENTO", conta_id_db=None):
        """
        Conecta à API IQ Option e seleciona o tipo de conta desejado.
        
        Parâmetros:
            email (str): Email cadastrado na IQ Option
            senha (str): Senha cadastrada na IQ Option
            tipo_conta (str): REAL, TREINAMENTO ou TORNEIO
            conta_id_db (int): ID da conta no banco de dados local (para atualização de perfil)
        
        Retorna:
            bool: True se a conexão foi bem-sucedida, False caso contrário
        """
        # Limpa o erro anterior
        self.ultimo_erro = None
        
        logger.info(f"Iniciando conexão com a IQ Option para o email: {email}")
        
        # Normaliza o tipo de conta desejado
        tipo_conta_desejado = tipo_conta.upper() if isinstance(tipo_conta, str) else "TREINAMENTO"
        if tipo_conta_desejado not in TIPO_CONTA:
            logger.warning(f"Tipo de conta desconhecido: {tipo_conta_desejado}. Usando TREINAMENTO.")
            tipo_conta_desejado = "TREINAMENTO"
        
        # Inicializa a conexão
        self.api = IQ_Option(email, senha)
        
        # Tenta conectar
        logger.info("Tentando estabelecer conexão WebSocket...")
        status, motivo = self.api.connect()
        
        if status:
            logger.info("Conexão WebSocket estabelecida com sucesso!")
            self.email = email
            self.conectado = True

            # --- Atualização do Perfil no DB --- 
            if conta_id_db is not None:
                logger.info(f"Tentando obter perfil da API para atualizar DB (conta_id={conta_id_db})...")
                try:
                    # Chama o método da API para obter o perfil
                    perfil_api = self.api.get_profile_ansyc() 
                    
                    if perfil_api and isinstance(perfil_api, dict):
                        logger.debug(f"Perfil obtido da API: {perfil_api}") 
                        # Tenta atualizar no banco de dados
                        # A função atualizar_perfil_conta_iq lida com campos ausentes
                        if atualizar_perfil_conta_iq(conta_id_db, perfil_api):
                            logger.info("Perfil IQ Option atualizado com sucesso no banco de dados local.")
                        else:
                            # Log de erro já é feito dentro da função atualizar_perfil_conta_iq
                            pass 
                    else:
                        logger.warning("Não foi possível obter dados válidos do perfil da API.")
                        
                except Exception as e_profile:
                    logger.error(f"Erro ao obter ou processar perfil da API: {e_profile}", exc_info=True)
            else:
                 logger.warning("conta_id_db não fornecido. Pulando atualização do perfil no DB.")
            # --- Fim da Atualização do Perfil --- 
            
            # Pequena pausa antes de tentar mudar/verificar conta
            time.sleep(1)

            # Tenta alterar para o tipo de conta desejado
            if self._selecionar_tipo_conta(tipo_conta_desejado):
                logger.info(f"Conta definida para {tipo_conta_desejado} após conexão.")
            else:
                logger.warning(f"Não foi possível definir conta para {tipo_conta_desejado}. Verificando conta ativa...")
                self._atualizar_saldo() # Atualiza saldo da conta ativa
                try:
                     current_mode = self.api.get_balance_mode()
                     logger.info(f"Modo de conta ativo obtido da API: {current_mode}")
                     for nome, codigo in TIPO_CONTA.items():
                         if codigo == current_mode: self.tipo_conta = nome; break
                except Exception as e_mode: logger.error(f"Erro ao obter modo de conta ativo: {e_mode}")

            logger.info(f"Conexão finalizada. Conta interna: {self.tipo_conta}, Saldo: {self.saldo} {self.moeda}")
            return True
        else:
            # Registra o erro de forma mais detalhada
            if isinstance(motivo, str):
                if "Falha na conexão de rede" in motivo:
                    logger.error(f"Erro de conexão: {motivo}")
                    self.ultimo_erro = motivo
                elif motivo == "2FA":
                    logger.info("Autenticação de dois fatores solicitada pela API")
                    self.ultimo_erro = "Autenticação de dois fatores solicitada. Entre em contato com o administrador."
                else:
                    logger.error(f"Falha na conexão WebSocket: {motivo}")
                    self.ultimo_erro = f"Falha na conexão: {motivo}"
            else:
                logger.error(f"Falha na conexão WebSocket com motivo desconhecido: {motivo}")
                self.ultimo_erro = "Falha na conexão com motivo desconhecido."
            
            self.conectado = False
            return False
    
    def _selecionar_tipo_conta(self, tipo_conta):
        """
        Seleciona o tipo de conta a ser usada. Atualiza self.tipo_conta e self.saldo.
        
        Parâmetros:
            tipo_conta (str): REAL, TREINAMENTO ou TORNEIO
        
        Retorna:
            bool: True se a mudança foi bem-sucedida e saldo atualizado, False caso contrário
        """
        if not self.conectado or not self.api:
            logger.error("Não conectado. Não é possível selecionar tipo de conta.")
            return False
        
        # Normaliza o tipo de conta alvo
        tipo_conta_alvo = tipo_conta.upper() if isinstance(tipo_conta, str) else "TREINAMENTO"
        codigo_tipo_alvo = TIPO_CONTA.get(tipo_conta_alvo, "PRACTICE")
        
        # Opcional: Verificar se já está na conta correta para evitar chamada desnecessária
        try:
            current_mode_api = self.api.get_balance_mode()
            if current_mode_api == codigo_tipo_alvo:
                logger.info(f"Já está na conta {tipo_conta_alvo}. Apenas atualizando saldo.")
                if self._atualizar_saldo(): # Garante que o saldo está atualizado
                    self.tipo_conta = tipo_conta_alvo # Confirma o tipo interno
                    return True
                else:
                    return False # Falha ao atualizar saldo
        except Exception as e_mode:
            logger.warning(f"Não foi possível verificar o modo de conta atual antes de mudar: {e_mode}")

        # Tenta mudar a conta
        logger.info(f"Tentando alterar para conta do tipo: {tipo_conta_alvo} (Código: {codigo_tipo_alvo})")
        resultado_change = None
        try:
            resultado_change = self.api.change_balance(codigo_tipo_alvo)
            logger.info(f"Resultado da chamada api.change_balance({codigo_tipo_alvo}): {resultado_change}")
            
            if resultado_change:
                logger.info(f"API retornou sucesso ao tentar alterar para {tipo_conta_alvo}. Aguardando para atualizar saldo...")
                time.sleep(1.5)  # Aumentar um pouco a pausa após a mudança bem-sucedida
                
                # Tenta atualizar o saldo após a mudança
                if self._atualizar_saldo():
                    self.tipo_conta = tipo_conta_alvo # Define o tipo interno APÓS sucesso
                    logger.info(f"Conta alterada e saldo atualizado com sucesso para: {tipo_conta_alvo}")
                    return True
                else:
                    logger.error(f"Conta {tipo_conta_alvo} alterada, MAS FALHOU ao atualizar o saldo após a mudança.")
                    # Mantém self.tipo_conta como None ou o anterior? Por segurança, None.
                    self.tipo_conta = None 
                    return False # Falha na operação completa
            else:
                logger.error(f"API retornou FALHA ao tentar alterar para o tipo de conta: {tipo_conta_alvo}")
                return False # API rejeitou a mudança
                
        except Exception as e:
            logger.error(f"EXCEÇÃO ao tentar alterar tipo de conta para {tipo_conta_alvo}: {e}", exc_info=True)
            logger.error(f"Valor retornado por change_balance antes da exceção (se houve): {resultado_change}")
            return False
    
    def _atualizar_saldo(self):
        """
        Atualiza as informações de saldo (self.saldo, self.moeda).
        Retorna True se sucesso, False caso contrário.
        """
        if not self.conectado or not self.api:
            logger.error("Não conectado. Não é possível obter saldo.")
            return False
        
        try:
            logger.debug("Chamando api.get_balance() e api.get_currency()...")
            self.saldo = self.api.get_balance()
            self.moeda = self.api.get_currency()
            logger.info(f"Saldo obtido da API: {self.saldo} {self.moeda}")
            if self.saldo is None or self.moeda is None:
                 logger.error("API retornou None para saldo ou moeda.")
                 return False
            return True
        except Exception as e:
            logger.error(f"Erro ao obter saldo/moeda da API: {e}", exc_info=True)
            self.saldo = 0.0 # Zera em caso de erro
            self.moeda = None
            return False
    
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
        Retorna as informações atuais da conta (estado interno da classe).
        """
        return {
            "email": self.email,
            "tipo_conta": self.tipo_conta, # Pode ser None se a seleção falhou
            "saldo": self.saldo,
            "moeda": self.moeda,
            "conectado": self.conectado,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ultimo_erro": self.ultimo_erro
        }

# Função auxiliar foi removida pois o fluxo mudou 