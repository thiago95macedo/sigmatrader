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

# Importa módulos da aplicação
from iqoption import LoginIQOption, listar_ativos_abertos_com_payout
from data import (
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
    atualizar_perfil_conta_iq,
    obter_perfil_conta_local,
)

# --- Constantes --- #
LOG_DIR = "log"
LOG_PATH = os.path.join(LOG_DIR, "sigmatrader.log")
SEPARATOR = "=" * 60  # Separador visual
TIPOS_CONTA_MAP = { "1": "TREINAMENTO", "2": "REAL", "3": "TORNEIO" }
MERCADOS_MAP = { "1": "Binário/Turbo", "2": "Digital", "3": "Forex", "4": "Cripto" }

# --- Configuração de Logging --- #
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

# Silencia logs de bibliotecas de terceiros no terminal
try:
    logging.getLogger('iqoptionapi.ws.client').setLevel(logging.WARNING)
    logging.getLogger('iqoptionapi.api').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
except Exception as e_log:
    logger.warning(f"Não foi possível silenciar logger(s) da biblioteca: {e_log}")

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

def press_enter_to_continue():
    input("\nPressione Enter para continuar...")

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
    
    tipo_conta = TIPOS_CONTA_MAP.get(opcao_tipo, "TREINAMENTO")
    
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

def login_iqoption(conta_detalhes, tipo_conta_selecionado):
    """
    Realiza login e seleciona o tipo de conta.
    Retorna (LoginIQOption, conta_id) ou (None, None).
    """
    if not conta_detalhes or len(conta_detalhes) < 5: logger.error("..."); print_error("..."); return None, None
    conta_id, nome, email, senha, _ = conta_detalhes
    
    print_header(f"Login para {nome}")
    print(f"  Tentando conectar e selecionar conta '{tipo_conta_selecionado}'...")
    
    login_manager = LoginIQOption()
    if login_manager.conectar(email, senha, tipo_conta=tipo_conta_selecionado, conta_id_db=conta_id):
        info = login_manager.obter_info_conta()
        tipo_ativo_real = info.get('tipo_conta')
        
        if tipo_ativo_real == tipo_conta_selecionado:
            print_success(f"Conectado! Conta ativa: {tipo_ativo_real} (Saldo: {info.get('saldo', 0.0):.2f} {info.get('moeda', '')})")
        else:
            logger.warning(f"Após conexão, tipo ativo ('{tipo_ativo_real}') difere do solicitado ('{tipo_conta_selecionado}').")
            print_error(f"Falha ao ativar conta {tipo_conta_selecionado}. Conta ativa atual: {tipo_ativo_real or 'Desconhecida'}. Saldo exibido pode ser de outra conta.")
            print(f"  Saldo atual (API): {info.get('saldo', 0.0):.2f} {info.get('moeda', '')}")

        tipo_para_db = tipo_ativo_real or tipo_conta_selecionado 
        print_info(f"Atualizando saldo {tipo_para_db} no banco de dados...")
        atualizar_saldos_conta(conta_id, tipo_para_db, info['saldo'], info['moeda'])
            
        return login_manager, conta_id
    else:
        print_error(f"Falha ao conectar à IQ Option para {email}. Verifique credenciais/conexão.")
        return None, None

def selecionar_tipo_conta_interface(default_tipo="TREINAMENTO"):
    """Interface para escolher tipo de conta antes de conectar."""
    print_header("Seleção de Tipo de Conta")
    print("  Qual tipo de conta usar?")
    print("    1. Treinamento")
    print("    2. Real")
    print("    3. Torneio")
    while True:
        opcao = input(f"  Opção (padrão: {default_tipo[0]}): ").strip()
        if not opcao: return default_tipo
        tipo_selecionado = TIPOS_CONTA_MAP.get(opcao)
        if tipo_selecionado: return tipo_selecionado
        else: print_error("Opção inválida.")

def selecionar_mercado_ativo():
    """Permite ao usuário escolher o mercado (tipo de ativo) para operar."""
    print_header("Seleção de Mercado")
    print("  Qual mercado operar?")
    print("    1. Binário / Turbo")
    print("    2. Digital")
    print("    3. Forex")
    print("    4. Cripto")
    
    while True:
        opcao = input("  Opção: ").strip()
        mercado_selecionado = MERCADOS_MAP.get(opcao)
        if mercado_selecionado:
            print_success(f"Mercado '{mercado_selecionado}' selecionado.")
            return mercado_selecionado
        else:
            print_error("Opção inválida. Escolha 1, 2, 3 ou 4.")

def exibir_ativos_abertos(iq_session, mercado_foco):
    """Busca e exibe os ativos abertos para o mercado selecionado, com payout."""
    print_header(f"Ativos Abertos - {mercado_foco}")
    print_info("Buscando...")
    
    # Chama a função que retorna lista de tuplas (ativo, payout)
    ativos_com_detalhes = listar_ativos_abertos_com_payout(iq_session.api, mercado_foco=mercado_foco) 
    
    if ativos_com_detalhes is None:
        print_error("Não foi possível obter a lista de ativos/detalhes. Verifique a conexão ou os logs.")
        return
        
    if not ativos_com_detalhes:
        print_info(f"Nenhum ativo encontrado aberto para o mercado {mercado_foco}.") 
        return
        
    # Define o título com base na disponibilidade de detalhes
    contem_payout = any(p is not None for _, p in ativos_com_detalhes)
    
    titulo_sucesso = f"Ativos {mercado_foco} ({len(ativos_com_detalhes)})"
    detalhes_str = []
    if contem_payout: detalhes_str.append("Payout")

    if detalhes_str:
        titulo_sucesso += f" - Ordenado por Payout ({', '.join(detalhes_str)})"
    else:
        titulo_sucesso += " - Abertos"
    print_success(titulo_sucesso)
    
    # Formatação em colunas 
    def formatar_item(ativo, payout):
        base = f"{ativo}"
        if payout is not None:
            base += f" ({payout}%)"
        return base
        
    itens_formatados = [formatar_item(a, p) for a, p in ativos_com_detalhes]
    col_width = max(len(item) for item in itens_formatados) + 2 # Espaço extra
    max_cols = 3 # Pode voltar para 3 colunas
    num_cols = min(max_cols, max(1, 100 // col_width))
    
    for i in range(0, len(itens_formatados), num_cols):
        linha_itens = itens_formatados[i:i+num_cols]
        print("    " + "".join(item.ljust(col_width) for item in linha_itens))

def menu_gerenciar_contas():
    """
    Exibe o menu para gerenciar contas e retorna a sessão de login se selecionada.
    """
    while True: # Loop para voltar ao menu após cadastro/exclusão
        print_header("Gerenciamento de Contas")
        
        contas = listar_contas()
        
        if not contas:
            print("  Nenhuma conta cadastrada.")
            cadastrar_nova = input("\n  Cadastrar nova conta? (S/n): ")
            if cadastrar_nova.lower() != 'n':
                cadastrar_conta_interface()
                continue # Volta ao início do loop para mostrar a nova conta
            else:
                return None # Sai se não quiser cadastrar
        
        print("  Contas cadastradas:")
        for i, (id_conta, nome, email, tipo_conta) in enumerate(contas, 1):
            print(f"    {i}. {nome} ({email}) - Padrão: {tipo_conta}")
        
        print("\n  Opções:")
        print("    1. Selecionar conta")
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
                        return conta_detalhes # Retorna os detalhes da conta selecionada
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
            press_enter_to_continue() # Pausa para o usuário ler

def menu_principal(iq_session, conta_id, tipo_conta_foco, mercado_foco):
    """Exibe o menu principal focado no tipo de conta e mercado."""
    while True:
        info = iq_session.obter_info_conta() # Pega info atual da API (pode ter mudado saldo)
        saldos_db = obter_saldos_conta(conta_id) # Pega saldos do DB
        
        # Determina qual saldo mostrar com base no foco
        saldo_foco_db = 0.0
        moeda_db = "USD"
        if saldos_db:
            moeda_db = saldos_db.get("moeda", "USD")
            if tipo_conta_foco == "REAL": saldo_foco_db = saldos_db.get("saldo_real", 0.0)
            elif tipo_conta_foco == "TREINAMENTO": saldo_foco_db = saldos_db.get("saldo_treinamento", 0.0)
            elif tipo_conta_foco == "TORNEIO": saldo_foco_db = saldos_db.get("saldo_torneio", 0.0)

        print_header(f"MENU: {tipo_conta_foco} | {mercado_foco}")
        print(f"  IQ Option: {info.get('tipo_conta', 'N/A')} ({info.get('saldo', 0.0):.2f} {info.get('moeda', '')})  |  BD Saldo Foco: {saldo_foco_db:.2f}")
        print(SEPARATOR)
        
        print("  Opções:")
        print(f"  1. Sincronizar Saldo {tipo_conta_foco} no BD")
        print(f"  2. Listar Ativos {mercado_foco}")
        print("  3. Trocar Tipo Conta (Sessão)")
        print("  4. Trocar Mercado (Sessão)")
        print("  5. Detalhes da Conta")
        print("  0. Deslogar")
        
        opcao = input("\n  Escolha: ").strip()
        
        if opcao == '1':
            if info.get('tipo_conta') == tipo_conta_foco:
                print_info(f"Sincronizando saldo {tipo_conta_foco}...")
                if atualizar_saldos_conta(conta_id, tipo_conta_foco, info['saldo'], info['moeda']):
                    print_success("Saldo BD atualizado!")
                else: print_error("Falha ao atualizar BD.")
            else: print_error(f"Conta ativa ({info.get('tipo_conta')}) não é a de foco ({tipo_conta_foco}). Use opção 3.")
            press_enter_to_continue()
            
        elif opcao == '2':
            exibir_ativos_abertos(iq_session, mercado_foco)
            press_enter_to_continue()

        elif opcao == '3':
            # Usa a função de seleção de tipo, mas não a de interface completa
            print("\n  Escolha novo tipo:")
            print("    1. Treinamento")
            print("    2. Real")
            print("    3. Torneio")
            tipo_opcao = input("  Opção: ").strip()
            novo_tipo = TIPOS_CONTA_MAP.get(tipo_opcao)
            if novo_tipo:
                print_info(f"Tentando alterar para conta {novo_tipo}...")
                if iq_session._selecionar_tipo_conta(novo_tipo):
                    print_success(f"Conta IQ alterada para {novo_tipo}.")
                    tipo_conta_foco = novo_tipo # Atualiza o foco
                    info_atualizada = iq_session.obter_info_conta() # Pega novo saldo
                    atualizar_saldos_conta(conta_id, novo_tipo, info_atualizada['saldo'], info_atualizada['moeda']) # Atualiza DB
                else: print_error(f"Falha ao alterar para {novo_tipo}.")
            else: print_error("Opção inválida.")
            press_enter_to_continue()

        elif opcao == '4':
            # Permite trocar o MERCADO para a sessão atual
            novo_mercado = selecionar_mercado_ativo()
            if novo_mercado:
                mercado_foco = novo_mercado # Atualiza o foco da sessão
            press_enter_to_continue()

        elif opcao == '5':
            # Busca os dados do perfil local antes de exibir
            perfil_local = obter_perfil_conta_local(conta_id)
            exibir_detalhes_conta(info, saldos_db, perfil_local) # Passa os dados do perfil
            press_enter_to_continue()
            
        elif opcao == '0':
            print_info("Deslogando e encerrando aplicação...")
            break # Sai do loop do menu principal
        
        else:
            print_error("Opção inválida.")
            press_enter_to_continue()

def obter_saldo_foco_db(saldos_db, tipo_conta_foco):
    """Retorna o saldo do BD para o tipo de conta em foco."""
    if not saldos_db: return 0.0
    if tipo_conta_foco == "REAL": return saldos_db.get("saldo_real", 0.0)
    if tipo_conta_foco == "TREINAMENTO": return saldos_db.get("saldo_treinamento", 0.0)
    if tipo_conta_foco == "TORNEIO": return saldos_db.get("saldo_torneio", 0.0)
    return 0.0

def exibir_detalhes_conta(info_api, saldos_db, perfil_local=None):
    """Mostra informações detalhadas da API, do BD e do perfil local."""
    print_header("Detalhes da Conta")
    
    print("[ IQ Option (API - Tempo Real) ]")
    print(f"  Email: {info_api.get('email')}")
    print(f"  Tipo Ativo: {info_api.get('tipo_conta', 'N/A')}")
    print(f"  Saldo Ativo: {info_api.get('saldo', 0.0):.2f} {info_api.get('moeda', '')}")
    print(f"  Conectado: {'Sim' if info_api.get('conectado') else 'Não'}")
    print(f"  Timestamp: {info_api.get('timestamp')}")
    
    print("\n[ Banco de Dados (Local - Saldos) ]")
    if saldos_db:
        print(f"  Saldo Real:        {saldos_db.get('saldo_real', 0.0):.2f} {saldos_db.get('moeda')}")
        print(f"  Saldo Treinamento: {saldos_db.get('saldo_treinamento', 0.0):.2f} {saldos_db.get('moeda')}")
        print(f"  Saldo Torneio:     {saldos_db.get('saldo_torneio', 0.0):.2f} {saldos_db.get('moeda')}")
        print(f"  Última Atualização: {saldos_db.get('ultima_atualizacao', 'N/A')}")
    else:
        print("  Saldos locais não disponíveis.")
        
    print("\n[ Banco de Dados (Local - Perfil IQ Option) ]")
    if perfil_local:
        print(f"  ID Usuário IQ: {perfil_local.get('iq_user_id', 'N/A')}")
        print(f"  Nome IQ:       {perfil_local.get('iq_name', 'N/A')}")
        print(f"  Nickname IQ:   {perfil_local.get('iq_nickname', 'N/A')}")
        # print(f"  Avatar URL:    {perfil_local.get('iq_avatar_url', 'N/A')}") # Descomentar se quiser mostrar a URL
    else:
        print("  Dados do perfil IQ Option ainda não sincronizados localmente.")

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
    
    # Loop principal: Gerencia Contas -> Seleciona Tipo -> Conecta -> Seleciona Mercado -> Menu Operacional
    while True:
        # 1. Gerenciar/Selecionar Conta
        conta_selecionada_detalhes = menu_gerenciar_contas()
        if not conta_selecionada_detalhes:
            # Usuário escolheu sair do gerenciamento
            print_info("Encerrando aplicação.")
            logger.info("Usuário optou por não selecionar conta. Encerrando SigmaTrader.")
            return
        
        # 2. Selecionar Tipo de Conta para a Sessão
        # Usa o tipo padrão da conta como default na interface
        tipo_conta_padrao = conta_selecionada_detalhes[4] or "TREINAMENTO"
        tipo_conta_foco = selecionar_tipo_conta_interface(tipo_conta_padrao)
        if not tipo_conta_foco: continue # Volta ao gerenciamento se a seleção falhar (improvável)

        # 3. Tentar Conectar com o Tipo Selecionado
        iq_session, conta_id = login_iqoption(conta_selecionada_detalhes, tipo_conta_foco)
        
        if iq_session and conta_id:
            # 4. Selecionar Mercado
            mercado_foco = selecionar_mercado_ativo()
            if not mercado_foco: continue # Volta ao gerenciamento se falhar
            
            # 5. Entrar no Menu Principal Operacional
            menu_principal(iq_session, conta_id, tipo_conta_foco, mercado_foco)
            
            # Se sair do menu_principal (opção 0), encerra a aplicação
            return
            
        else:
            # Falha no login
            print_info("Login na IQ Option falhou.")
            # O loop continua, voltando para o gerenciamento de contas

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