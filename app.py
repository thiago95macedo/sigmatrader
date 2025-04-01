#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SigmaTrader - Aplicação principal
Ferramenta para trading automatizado usando a API IQ Option
"""

import os
import sys
import sqlite3
import logging
import getpass
import platform
from datetime import datetime

# Importa o módulo de login para IQ Option
from iqoption.login import LoginIQOption, fazer_login

# Constantes
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "sigmatrader.db")
LOG_DIR = "log"
LOG_PATH = os.path.join(LOG_DIR, "sigmatrader.log")

# Verifica se o diretório de logs existe
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_password_with_asterisks(prompt="Senha: "):
    """
    Função para obter a senha do usuário mostrando asteriscos
    """
    senha = ""
    
    # Importa módulos específicos para cada sistema operacional
    try:
        if platform.system() == "Windows":
            import msvcrt
            print(prompt, end="", flush=True)
            
            while True:
                ch = msvcrt.getch()
                if ch == b'\r' or ch == b'\n':  # Enter
                    print()
                    break
                elif ch == b'\x08':  # Backspace
                    if len(senha) > 0:
                        # Remove o último caractere da senha e da tela
                        senha = senha[:-1]
                        print("\b \b", end="", flush=True)
                else:
                    senha += ch.decode("latin-1")
                    print("*", end="", flush=True)
        else:
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            try:
                print(prompt, end="", flush=True)
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
        # Se não conseguir importar os módulos específicos,
        # usa o getpass padrão como fallback
        senha = getpass.getpass(prompt)
    except Exception as e:
        # Em caso de qualquer erro, utiliza o getpass padrão
        logger.error(f"Erro ao capturar senha com asteriscos: {e}")
        senha = getpass.getpass(prompt)
        
    return senha

def inicializar_banco_dados():
    """
    Verifica a existência do banco de dados e o cria caso não exista
    """
    logger.info("Verificando banco de dados...")
    
    # Verifica se o diretório data existe
    if not os.path.exists(DB_DIR):
        logger.info(f"Criando diretório {DB_DIR}")
        os.makedirs(DB_DIR)
    
    # Verifica se o banco de dados existe
    if os.path.exists(DB_PATH):
        logger.info(f"Banco de dados encontrado em {DB_PATH}")
        return True
    
    # Cria o banco de dados e as tabelas iniciais
    logger.info(f"Criando banco de dados em {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela de configurações
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            id INTEGER PRIMARY KEY,
            chave TEXT UNIQUE NOT NULL,
            valor TEXT NOT NULL,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Tabela de contas IQ Option
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contas_iqoption (
            id INTEGER PRIMARY KEY,
            nome_completo TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo_conta TEXT DEFAULT 'TREINAMENTO',
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acesso TIMESTAMP,
            ativo BOOLEAN DEFAULT 1
        )
        ''')
        
        # Tabela de operações
        cursor.execute('''
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
        
        # Tabela de histórico de ativos
        cursor.execute('''
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
        
        # Insere algumas configurações iniciais
        cursor.execute('''
        INSERT INTO configuracoes (chave, valor) VALUES 
        ('versao', '1.0.0'),
        ('data_criacao', ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        
        conn.commit()
        logger.info("Banco de dados inicializado com sucesso!")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Erro ao criar banco de dados: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_contas_existentes():
    """
    Verifica se existem contas IQ Option cadastradas
    Retorna o número de contas encontradas
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM contas_iqoption WHERE ativo = 1")
        quantidade = cursor.fetchone()[0]
        
        return quantidade
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar contas: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def listar_contas():
    """
    Lista todas as contas IQ Option cadastradas
    Retorna uma lista de tuplas (id, nome, email)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nome_completo, email, tipo_conta FROM contas_iqoption WHERE ativo = 1")
        contas = cursor.fetchall()
        
        return contas
    except sqlite3.Error as e:
        logger.error(f"Erro ao listar contas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def cadastrar_conta():
    """
    Cadastra uma nova conta IQ Option
    """
    print("\n=== Cadastro de Conta IQ Option ===")
    
    nome_completo = input("Nome completo: ")
    email = input("Email: ")
    
    # Verifica se o email já existe
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM contas_iqoption WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"Erro: O email {email} já está cadastrado.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Erro ao verificar email: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    # Continua com o cadastro - agora usa a função personalizada para a senha
    senha = get_password_with_asterisks("Senha: ")
    
    # Seleciona o tipo de conta padrão
    print("\nSelecione o tipo de conta padrão:")
    print("1. Conta de Treinamento (Demo)")
    print("2. Conta Real")
    print("3. Conta de Torneio")
    
    opcao_tipo = input("Opção (padrão: 1): ").strip()
    
    if opcao_tipo == "2":
        tipo_conta = "REAL"
    elif opcao_tipo == "3":
        tipo_conta = "TORNEIO"
    else:
        tipo_conta = "TREINAMENTO"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO contas_iqoption (nome_completo, email, senha, tipo_conta)
        VALUES (?, ?, ?, ?)
        """, (nome_completo, email, senha, tipo_conta))
        
        conn.commit()
        print(f"Conta cadastrada com sucesso para {nome_completo}!")
        logger.info(f"Nova conta cadastrada para o email {email}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao cadastrar conta: {e}")
        print(f"Erro ao cadastrar conta: {e}")
        return False
    finally:
        if conn:
            conn.close()

def obter_detalhes_conta(conta_id):
    """
    Obtém os detalhes de uma conta específica
    Retorna uma tupla (id, nome, email, senha, tipo_conta)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nome_completo, email, senha, tipo_conta FROM contas_iqoption WHERE id = ?", (conta_id,))
        conta = cursor.fetchone()
        
        return conta
    except sqlite3.Error as e:
        logger.error(f"Erro ao obter detalhes da conta {conta_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def deletar_conta(conta_id):
    """
    Marca uma conta como inativa (soft delete)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a conta existe
        cursor.execute("SELECT nome_completo FROM contas_iqoption WHERE id = ?", (conta_id,))
        conta = cursor.fetchone()
        
        if not conta:
            print("Conta não encontrada.")
            return False
        
        # Confirmar exclusão
        confirmacao = input(f"Tem certeza que deseja excluir a conta de {conta[0]}? (s/n): ")
        if confirmacao.lower() != 's':
            print("Operação cancelada.")
            return False
        
        # Marca a conta como inativa (soft delete)
        cursor.execute("UPDATE contas_iqoption SET ativo = 0 WHERE id = ?", (conta_id,))
        conn.commit()
        
        print(f"Conta de {conta[0]} excluída com sucesso.")
        logger.info(f"Conta {conta_id} marcada como inativa")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao excluir conta {conta_id}: {e}")
        print(f"Erro ao excluir conta: {e}")
        return False
    finally:
        if conn:
            conn.close()

def registrar_acesso(conta_id):
    """
    Registra o último acesso de uma conta
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE contas_iqoption 
        SET ultimo_acesso = ? 
        WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), conta_id))
        
        conn.commit()
        logger.info(f"Acesso registrado para conta {conta_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erro ao registrar acesso para conta {conta_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

def login_iqoption(conta_detalhes):
    """
    Realiza login na plataforma IQ Option usando o módulo de login
    
    Parâmetros:
        conta_detalhes: Detalhes da conta (id, nome, email, senha, tipo_conta)
        
    Retorna:
        LoginIQOption: O gerenciador de login ou None em caso de falha
    """
    if not conta_detalhes or len(conta_detalhes) < 5:
        logger.error("Detalhes da conta incompletos ou inválidos")
        return None
    
    _, nome, email, senha, tipo_conta = conta_detalhes
    
    print(f"\nRealizando login para {nome}...")
    print(f"Tipo de conta: {tipo_conta}")
    
    # Cria o gerenciador de login
    login_manager = LoginIQOption()
    
    # Tenta conectar
    if login_manager.conectar(email, senha, tipo_conta):
        # Obtém informações da conta
        info = login_manager.obter_info_conta()
        print(f"\nConexão estabelecida com sucesso!")
        print(f"Saldo atual: {info['saldo']} {info['moeda']}")
        return login_manager
    else:
        print("\nFalha ao conectar à IQ Option. Verifique suas credenciais.")
        return None

def menu_gerenciar_contas():
    """
    Exibe o menu para gerenciar contas
    """
    print("\n=== Gerenciamento de Contas IQ Option ===")
    
    contas = listar_contas()
    
    if not contas:
        print("Não há contas cadastradas.")
        cadastrar_nova = input("Deseja cadastrar uma nova conta? (s/n): ")
        if cadastrar_nova.lower() == 's':
            cadastrar_conta()
            return None
        return None
    
    print("\nContas cadastradas:")
    for i, (id_conta, nome, email, tipo_conta) in enumerate(contas, 1):
        print(f"{i}. {nome} ({email}) - {tipo_conta}")
    
    print("\nOpções:")
    print("1. Selecionar uma conta")
    print("2. Cadastrar nova conta")
    print("3. Excluir uma conta")
    print("0. Sair")
    
    opcao = input("\nEscolha uma opção: ")
    
    if opcao == '1':
        num_conta = input("Selecione o número da conta: ")
        try:
            indice = int(num_conta) - 1
            if 0 <= indice < len(contas):
                conta_id = contas[indice][0]
                conta = obter_detalhes_conta(conta_id)
                if conta:
                    registrar_acesso(conta_id)
                    # Realiza login na IQ Option
                    login_manager = login_iqoption(conta)
                    return login_manager
                else:
                    print("Erro ao obter detalhes da conta.")
                    return None
            else:
                print("Número de conta inválido.")
                return None
        except ValueError:
            print("Entrada inválida. Digite o número da conta.")
            return None
    
    elif opcao == '2':
        cadastrar_conta()
        return None
    
    elif opcao == '3':
        num_conta = input("Selecione o número da conta a excluir: ")
        try:
            indice = int(num_conta) - 1
            if 0 <= indice < len(contas):
                conta_id = contas[indice][0]
                deletar_conta(conta_id)
            else:
                print("Número de conta inválido.")
        except ValueError:
            print("Entrada inválida. Digite o número da conta.")
        return None
    
    elif opcao == '0':
        return None
    
    else:
        print("Opção inválida.")
        return None

def main():
    """Função principal da aplicação"""
    logger.info("Iniciando SigmaTrader...")
    
    # Inicializa o banco de dados
    if not inicializar_banco_dados():
        logger.error("Falha ao inicializar o banco de dados. Encerrando aplicação.")
        return
    
    print("\n===== Bem-vindo ao SigmaTrader =====")
    print("Sistema de trading automatizado para IQ Option")
    
    # Verifica se existem contas cadastradas
    num_contas = verificar_contas_existentes()
    
    if num_contas == 0:
        print("\nNenhuma conta IQ Option cadastrada.")
        print("Para começar, você precisa cadastrar uma conta.")
        cadastrar_conta()
    
    # Gerenciamento de contas e login
    iq_session = None
    while iq_session is None:
        iq_session = menu_gerenciar_contas()
        
        if iq_session is None:
            continuar = input("\nDeseja tentar novamente? (s/n): ")
            if continuar.lower() != 's':
                break
    
    if iq_session:
        # Se temos uma sessão válida, inicia as operações
        print("\nIniciando operações com a conta selecionada...")
        # Aqui viriam as próximas funcionalidades do sistema
        
        # Por enquanto, apenas exibe as informações da conta
        info = iq_session.obter_info_conta()
        print(f"\nInformações da conta:")
        print(f"Email: {info['email']}")
        print(f"Tipo de conta: {info['tipo_conta']}")
        print(f"Saldo: {info['saldo']} {info['moeda']}")
        print(f"Status: {'Conectado' if info['conectado'] else 'Desconectado'}")
    else:
        print("\nNenhuma conta selecionada. Encerrando aplicação.")
    
    logger.info("Encerrando SigmaTrader")

if __name__ == "__main__":
    main() 