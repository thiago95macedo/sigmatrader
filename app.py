#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SigmaTrader - Aplicação principal
Ferramenta para trading automatizado usando a API IQ Option
"""

import os
import sys
import logging
import getpass
import platform
from datetime import datetime

# Importa o módulo de login para IQ Option
from iqoption.login import LoginIQOption

# Importa as funções de banco de dados
from data.database import (
    inicializar_banco_dados,
    verificar_contas_existentes,
    listar_contas,
    verificar_email_existente,
    cadastrar_conta_db,
    obter_detalhes_conta,
    obter_nome_conta,
    deletar_conta_db,
    registrar_acesso,
    obter_saldos_conta,
    atualizar_saldos_conta,
    obter_id_conta_atual,
)

# --- Constantes --- #
LOG_DIR = "log"
LOG_PATH = os.path.join(LOG_DIR, "sigmatrader.log")
SEPARATOR = "=" * 60  # Separador visual

# --- Configuração de Logging --- #
# Verifica se o diretório de logs existe
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Funções de Interface Auxiliares --- #
def print_header(title):
    """Imprime um cabeçalho formatado."""
    print(f"\n{SEPARATOR}")
    print(f"# {title.upper()} #")
    print(SEPARATOR)

def print_error(message):
    """Imprime uma mensagem de erro formatada."""
    print(f"\n[ERRO] {message}")

def print_success(message):
    """Imprime uma mensagem de sucesso formatada."""
    print(f"\n[SUCESSO] {message}")

def print_info(message):
    """Imprime uma mensagem informativa formatada."""
    print(f"\n[INFO] {message}")

def get_password_with_asterisks(prompt="Senha: "):
    """
    Função para obter a senha do usuário mostrando asteriscos
    """
    senha = ""
    print(prompt, end="", flush=True)
    try:
        if platform.system() == "Windows":
            import msvcrt
            while True:
                ch = msvcrt.getch()
                if ch == b'\r' or ch == b'\n':  # Enter
                    print()
                    break
                elif ch == b'\x08':  # Backspace
                    if len(senha) > 0:
                        senha = senha[:-1]
                        print("\b \b", end="", flush=True)
                else:
                    try:
                        char = ch.decode("cp850") # Tenta decodificar
                        senha += char
                        print("*", end="", flush=True)
                    except UnicodeDecodeError:
                        pass # Ignora caracteres não decodificáveis
        else:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch == '\r' or ch == '\n':  # Enter
                        print()
                        break
                    elif ch == '\x7f' or ch == '\x08':  # Backspace
                        if len(senha) > 0:
                            senha = senha[:-1]
                            print("\b \b", end="", flush=True)
                    else:
                        senha += ch
                        print("*", end="", flush=True)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
    except ImportError:
        logger.warning("Módulos específicos de OS não encontrados para input de senha. Usando getpass.")
        senha = getpass.getpass(prompt="") # Prompt já foi impresso
    except Exception as e:
        logger.error(f"Erro ao capturar senha com asteriscos: {e}")
        senha = getpass.getpass(prompt="")
        
    return senha

# --- Funções de Interface Principais --- #
def cadastrar_conta_interface():
    """
    Interface para cadastrar uma nova conta IQ Option
    """
    print_header("Cadastro de Nova Conta IQ Option")
    
    nome_completo = input("  Nome completo: ")
    email = input("  Email: ")
    
    # Verifica se o email já existe
    if verificar_email_existente(email):
        print_error(f"O email '{email}' já está cadastrado.")
        return False
    
    # Pede a senha
    senha = get_password_with_asterisks("  Senha: ")
    
    # Seleciona o tipo de conta padrão
    print("\n  Selecione o tipo de conta padrão:")
    print("    1. Treinamento (Demo)")
    print("    2. Real")
    print("    3. Torneio")
    
    opcao_tipo = input("  Opção (padrão: 1): ").strip()
    
    if opcao_tipo == "2":
        tipo_conta = "REAL"
    elif opcao_tipo == "3":
        tipo_conta = "TORNEIO"
    else:
        tipo_conta = "TREINAMENTO"
    
    # Chama a função do DB para cadastrar
    if cadastrar_conta_db(nome_completo, email, senha, tipo_conta):
        print_success(f"Conta para '{nome_completo}' cadastrada com sucesso!")
        return True
    else:
        print_error(f"Falha ao cadastrar conta no banco de dados.")
        return False

def deletar_conta_interface(conta_id):
    """
    Interface para excluir uma conta
    """
    nome_conta = obter_nome_conta(conta_id)
    
    if not nome_conta:
        print_error("Conta não encontrada.")
        return False
        
    # Confirmar exclusão
    confirmacao = input(f"\n  Tem certeza que deseja excluir a conta de '{nome_conta}'? (s/N): ")
    if confirmacao.lower() != 's':
        print_info("Operação cancelada.")
        return False
        
    # Chama a função do DB para deletar
    if deletar_conta_db(conta_id):
        print_success(f"Conta de '{nome_conta}' excluída com sucesso.")
        return True
    else:
        print_error(f"Falha ao excluir conta no banco de dados.")
        return False

def login_iqoption(conta_detalhes):
    """
    Realiza login na plataforma IQ Option e atualiza os saldos no DB.
    """
    if not conta_detalhes or len(conta_detalhes) < 5:
        logger.error("Detalhes da conta incompletos ou inválidos para login")
        print_error("Dados internos da conta inválidos para login.")
        return None
    
    conta_id, nome, email, senha, tipo_conta_inicial = conta_detalhes
    
    print_header(f"Login para {nome}")
    print(f"  Tentando conectar com a conta '{tipo_conta_inicial}'...")
    
    # Cria o gerenciador de login
    login_manager = LoginIQOption()
    
    # Tenta conectar
    if login_manager.conectar(email, senha, tipo_conta_inicial):
        info = login_manager.obter_info_conta()
        print_success(f"Conexão estabelecida com sucesso!")
        print(f"  Saldo atual ({info['tipo_conta']}): {info['saldo']:.2f} {info['moeda']}")
        
        # Atualiza o saldo correspondente no banco de dados
        tipo_conta_conectada = info['tipo_conta'] or "TREINAMENTO" # Usa Treinamento se None
        print(f"  Atualizando saldo {tipo_conta_conectada} no banco de dados...")
        if not atualizar_saldos_conta(conta_id, tipo_conta_conectada, info['saldo'], info['moeda']):
             logger.warning(f"Não foi possível atualizar o saldo {tipo_conta_conectada} da conta {conta_id} no DB.")
             print(f"  [AVISO] Não foi possível atualizar o saldo {tipo_conta_conectada} no banco de dados local.")
        
        # Exibe os saldos armazenados
        saldos = obter_saldos_conta(conta_id)
        if saldos:
            print("\n  Saldos Armazenados Localmente:")
            print(f"    Real:        {saldos['saldo_real']:.2f} {saldos['moeda']}")
            print(f"    Treinamento: {saldos['saldo_treinamento']:.2f} {saldos['moeda']}")
            print(f"    Torneio:     {saldos['saldo_torneio']:.2f} {saldos['moeda']}")
            print(f"    (Última atualização BD: {saldos['ultima_atualizacao']})" if saldos['ultima_atualizacao'] else "")
        
        return login_manager
    else:
        print_error("Falha ao conectar à IQ Option. Verifique suas credenciais e conexão.")
        return None

def menu_gerenciar_contas():
    """
    Exibe o menu para gerenciar contas e retorna a sessão de login se selecionada.
    """
    while True: # Loop para voltar ao menu após cadastro/exclusão
        print_header("Gerenciamento de Contas IQ Option")
        
        contas = listar_contas()
        
        if not contas:
            print("  Nenhuma conta cadastrada.")
            cadastrar_nova = input("\n  Deseja cadastrar uma nova conta? (S/n): ")
            if cadastrar_nova.lower() != 'n':
                cadastrar_conta_interface()
                continue # Volta ao início do loop para mostrar a nova conta
            else:
                return None # Sai se não quiser cadastrar
        
        print("  Contas cadastradas:")
        for i, (id_conta, nome, email, tipo_conta) in enumerate(contas, 1):
            print(f"    {i}. {nome} ({email}) - Padrão: {tipo_conta}")
        
        print("\n  Opções:")
        print("    1. Selecionar conta para login")
        print("    2. Cadastrar nova conta")
        print("    3. Excluir uma conta")
        print("    0. Voltar / Sair")
        
        opcao = input("\n  Escolha uma opção: ").strip()
        
        if opcao == '1':
            num_conta = input("    Selecione o número da conta: ")
            try:
                indice = int(num_conta) - 1
                if 0 <= indice < len(contas):
                    conta_id = contas[indice][0]
                    conta_detalhes = obter_detalhes_conta(conta_id)
                    if conta_detalhes:
                        registrar_acesso(conta_id)
                        login_manager = login_iqoption(conta_detalhes)
                        return login_manager # Retorna a sessão de login
                    else:
                        print_error("Não foi possível obter detalhes da conta selecionada.")
                        # Continua no loop
                else:
                    print_error("Número de conta inválido.")
            except ValueError:
                print_error("Entrada inválida. Por favor, digite o número da conta.")
        
        elif opcao == '2':
            cadastrar_conta_interface()
            # Continua no loop para mostrar o menu atualizado
        
        elif opcao == '3':
            num_conta = input("    Selecione o número da conta a excluir: ")
            try:
                indice = int(num_conta) - 1
                if 0 <= indice < len(contas):
                    conta_id = contas[indice][0]
                    deletar_conta_interface(conta_id)
                    # Continua no loop
                else:
                    print_error("Número de conta inválido.")
            except ValueError:
                print_error("Entrada inválida. Por favor, digite o número da conta.")
        
        elif opcao == '0':
            return None # Sai do gerenciamento de contas
        
        else:
            print_error("Opção inválida.")
            input("  Pressione Enter para continuar...") # Pausa para o usuário ler

def menu_principal(iq_session):
    """Exibe o menu principal da aplicação após o login."""
    while True:
        conta_id = obter_id_conta_atual(iq_session.email)
        info = iq_session.obter_info_conta()
        saldos_db = obter_saldos_conta(conta_id) if conta_id else None
        tipo_conta_ativa = info['tipo_conta'] or "TREINAMENTO"
        saldo_ativo_iq = info['saldo']
        moeda = info['moeda']

        print_header(f"Menu Principal - {info['email']}")
        print(f"  Conta Ativa IQ Option: {tipo_conta_ativa}")
        print(f"  Saldo Atual IQ Option: {saldo_ativo_iq:.2f} {moeda}")
        if saldos_db:
            print(f"  Saldo DB (Real):       {saldos_db['saldo_real']:.2f} {saldos_db['moeda']}")
            print(f"  Saldo DB (Treinamento):{saldos_db['saldo_treinamento']:.2f} {saldos_db['moeda']}")
            print(f"  Saldo DB (Torneio):    {saldos_db['saldo_torneio']:.2f} {saldos_db['moeda']}")
        print(SEPARATOR)
        
        print("  Opções:")
        print(f"    1. Atualizar saldo {tipo_conta_ativa} no Banco de Dados")
        print("    2. Ver informações detalhadas da conta")
        print("    3. Trocar tipo de conta na IQ Option")
        # Adicionar mais opções aqui (ex: Operar, Configurar, etc.)
        print("    0. Deslogar e Sair")
        
        opcao = input("\n  Escolha uma opção: ").strip()
        
        if opcao == '1':
            print_info(f"Atualizando saldo {tipo_conta_ativa} no BD...")
            if conta_id:
                if atualizar_saldos_conta(conta_id, tipo_conta_ativa, saldo_ativo_iq, moeda):
                    print_success(f"Saldo {tipo_conta_ativa} atualizado com sucesso no banco de dados!")
                else:
                    print_error("Falha ao atualizar saldo no banco de dados.")
            else:
                print_error("Não foi possível identificar a conta atual no banco de dados.")
            input("  Pressione Enter para continuar...")
            
        elif opcao == '2':
            print_header("Informações da Conta")
            print(f"  Email: {info['email']}")
            print(f"  Tipo de Conta Ativa (IQ): {tipo_conta_ativa}")
            print(f"  Saldo Atual (IQ): {saldo_ativo_iq:.2f} {moeda}")
            print(f"  Status Conexão: {'Conectado' if info['conectado'] else 'Desconectado'}")
            print(f"  Timestamp da Informação: {info['timestamp']}")
            if saldos_db:
                print("\n  Saldos Armazenados no BD:")
                print(f"    Real:        {saldos_db['saldo_real']:.2f} {saldos_db['moeda']}")
                print(f"    Treinamento: {saldos_db['saldo_treinamento']:.2f} {saldos_db['moeda']}")
                print(f"    Torneio:     {saldos_db['saldo_torneio']:.2f} {saldos_db['moeda']}")
                print(f"    Última atualização: {saldos_db['ultima_atualizacao']}")
            else:
                print("\n  Saldos no BD ainda não disponíveis.")
            input("  Pressione Enter para continuar...")
        
        elif opcao == '3':
            print_header("Trocar Tipo de Conta na IQ Option")
            print("    1. Treinamento")
            print("    2. Real")
            print("    3. Torneio")
            
            tipo_opcao = input("  Escolha o novo tipo de conta: ").strip()
            
            tipo_novo = None
            if tipo_opcao == '1': tipo_novo = "TREINAMENTO"
            elif tipo_opcao == '2': tipo_novo = "REAL"
            elif tipo_opcao == '3': tipo_novo = "TORNEIO"
            else: print_error("Opção inválida.")
                
            if tipo_novo:
                print_info(f"Tentando alterar para conta {tipo_novo}...")
                if iq_session._selecionar_tipo_conta(tipo_novo):
                    print_success(f"Tipo de conta na IQ Option alterado para: {tipo_novo}")
                    print(f"  Novo saldo atual: {iq_session.saldo:.2f} {iq_session.moeda}")
                    # Atualiza o saldo do novo tipo no banco de dados
                    if conta_id:
                        atualizar_saldos_conta(conta_id, tipo_novo, iq_session.saldo, iq_session.moeda)
                else:
                    print_error(f"Falha ao alterar para o tipo de conta {tipo_novo} na IQ Option.")
            input("  Pressione Enter para continuar...")
        
        elif opcao == '0':
            print_info("Deslogando e encerrando aplicação...")
            break # Sai do loop do menu principal
        
        else:
            print_error("Opção inválida.")
            input("  Pressione Enter para continuar...")

def main():
    """Função principal da aplicação"""
    logger.info("Iniciando SigmaTrader...")
    
    # Inicializa o banco de dados
    if not inicializar_banco_dados():
        print_error("Falha crítica ao inicializar o banco de dados. Verifique os logs.")
        logger.critical("Falha ao inicializar o banco de dados. Encerrando aplicação.")
        return
    
    print_header("Bem-vindo ao SigmaTrader")
    print("  Sistema de trading automatizado para IQ Option")
    print(SEPARATOR)
    
    # Verifica se existem contas cadastradas
    num_contas = verificar_contas_existentes()
    if num_contas == 0:
        print_info("Nenhuma conta IQ Option cadastrada.")
        print("  Para começar, vamos cadastrar sua primeira conta.")
        cadastrar_conta_interface()
    
    # Loop para Gerenciamento de Contas e Login
    iq_session = None
    while True:
        iq_session = menu_gerenciar_contas() # Entra no menu de gerenciamento
        
        if iq_session:
            break # Sai do loop se o login for bem-sucedido
        
        # Se saiu do menu sem logar (opção 0 ou falha)
        print_info("Nenhuma conta selecionada para login.")
        continuar = input("  Deseja tentar gerenciar/selecionar contas novamente? (S/n): ")
        if continuar.lower() == 'n':
            print_info("Encerrando aplicação.")
            logger.info("Usuário optou por não logar. Encerrando SigmaTrader.")
            return # Encerra a aplicação
        # Se a resposta for 's' ou vazia, o loop continua
            
    # Se chegou aqui, temos uma sessão de login válida
    print_success("Login realizado com sucesso!")
    menu_principal(iq_session) # Entra no menu principal da aplicação
    
    logger.info("Encerrando SigmaTrader")

# --- Execução Principal --- #
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperação interrompida pelo usuário.")
        logger.warning("Aplicação interrompida por KeyboardInterrupt.")
    except Exception as e:
        print(f"\n[ERRO FATAL] Ocorreu um erro inesperado: {e}")
        logger.critical(f"Erro fatal não tratado na execução principal: {e}", exc_info=True)
    finally:
        print("\nFinalizando...") 