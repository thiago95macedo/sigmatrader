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
import time

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
    logging.getLogger('websocket').setLevel(logging.WARNING)  # Silencia os logs de ping do websocket
except Exception as e_log:
    logger.warning(f"Não foi possível silenciar logger(s) da biblioteca: {e_log}")

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

# Importa módulos LSTM
try:
    from lstm.treinamento import treinar_modelo, atualizar_modelo
    from lstm.predicao import executar_operacoes_lstm, analisar_ativo_lstm
    LSTM_DISPONIVEL = True
except ImportError:
    LSTM_DISPONIVEL = False
    logger.warning("Módulos LSTM não disponíveis. Algumas funcionalidades estarão desabilitadas.")

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
    try:
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
            # Verifica se há informações de erro específicas no objeto login_manager
            if hasattr(login_manager, 'ultimo_erro') and login_manager.ultimo_erro:
                print_error(f"Falha ao conectar: {login_manager.ultimo_erro}")
            elif "name resolution" in str(login_manager.__dict__):
                print_error(f"Erro de conexão de rede: Não foi possível conectar ao servidor IQ Option. Verifique sua conexão com a internet.")
            else:
                print_error(f"Falha ao conectar à IQ Option para {email}. Verifique credenciais e conexão de rede.")
            return None, None
    except Exception as e:
        if "name resolution" in str(e):
            print_error(f"Erro de conexão de rede: Não foi possível conectar ao servidor IQ Option. Verifique sua conexão com a internet.")
        else:
            print_error(f"Erro inesperado ao conectar à IQ Option: {e}")
            logger.error(f"Exceção detalhada durante login: {e}", exc_info=True)
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

def exibir_ativos_abertos(iq_session, mercado_foco, payout_minimo=0, timeframe=1):
    """Exibe e retorna lista de ativos abertos para um mercado específico"""
    print_header(f"Ativos Abertos - {mercado_foco}")
    
    # Obter lista de ativos abertos com seus payouts
    print("  Buscando ativos abertos e payouts...")
    start_time = time.time()
    
    ativos = listar_ativos_abertos_com_payout(iq_session.api, mercado_foco, timeframe)
    
    if not ativos:
        print("\n  Nenhum ativo disponível para o mercado selecionado.")
        return []
        
    tempo_busca = time.time() - start_time
    
    # Filtrar por payout mínimo, se aplicável
    if payout_minimo > 0:
        ativos_filtrados = [(ativo, payout) for ativo, payout in ativos 
                           if payout is not None and payout >= payout_minimo]
    else:
        ativos_filtrados = ativos
    
    # Exibir resultado
    qtd_total = len(ativos)
    qtd_filtrada = len(ativos_filtrados)
    
    print(f"\n  ✅ Encontrados {qtd_total} ativos para {mercado_foco} (Timeframe: {timeframe} min)")
    print(f"     {qtd_filtrada} atendem ao payout mínimo de {payout_minimo}%")
    print(f"     Tempo para buscar: {tempo_busca:.2f} segundos")
    
    # Formatar e exibir a lista
    print("\n  " + "-" * 50)
    print(formatar_lista_ativos(ativos_filtrados))
    print("  " + "-" * 50)
    
    press_enter_to_continue()
    return ativos_filtrados

def formatar_lista_ativos(ativos):
    """
    Formata a exibição de uma lista de ativos em colunas para melhor visualização
    
    Args:
        ativos: Lista de tuplas (ativo, payout)
        
    Returns:
        String formatada com a lista de ativos em colunas
    """
    # Função auxiliar para formatar cada item
    def formatar_item(ativo, payout):
        if payout is not None:
            return f"{ativo} ({payout}%)"
        return ativo
    
    # Formata cada item e determina largura da coluna
    itens_formatados = [formatar_item(a, p) for a, p in ativos]
    col_width = max(len(item) for item in itens_formatados) + 2 if itens_formatados else 0  # Adiciona espaço
    max_cols = 3  # Número de colunas para exibição
    
    # Verifica se não há itens
    if not itens_formatados:
        return "    Nenhum ativo encontrado"
    
    # Calcula número de linhas necessárias
    num_itens = len(itens_formatados)
    num_linhas = (num_itens + max_cols - 1) // max_cols
    
    # Cria formato de coluna como string
    linhas = []
    for linha in range(num_linhas):
        linha_str = "    "  # Indentação
        for col in range(max_cols):
            idx = linha + col * num_linhas
            if idx < num_itens:
                item = itens_formatados[idx].ljust(col_width)
                linha_str += item
        linhas.append(linha_str)
    
    return "\n".join(linhas)

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
    """
    Menu principal da aplicação
    
    Args:
        iq_session: Sessão IQ Option conectada
        conta_id: ID da conta local
        tipo_conta_foco: Tipo de conta atual (real ou prática)
        mercado_foco: Mercado atual em foco
    
    Returns:
        Tupla (bool, str, str) indicando se deve continuar, tipo_conta e mercado
    """
    # Configuração padrão de payout mínimo
    global payout_minimo, timeframe_padrao
    payout_minimo = 85  # Percentual mínimo de lucro aceitável

    # Configuração padrão de timeframe
    timeframe_padrao = 1  # Timeframe em minutos (1, 5, 15, 30, 60, 240)
    
    executando = True
    
    while executando:
        # Obter informações atualizadas
        tipo_conta_atual = iq_session.api.get_balance_mode()
        saldo_api = iq_session.api.get_balance()
        moeda_api = iq_session.api.get_currency()
        saldos_db = obter_saldos_conta(conta_id)
        saldo_foco_db = obter_saldo_foco_db(saldos_db, tipo_conta_foco)
        
        print("\n" + "=" * 60)
        print(f"# MENU: {tipo_conta_foco} | {mercado_foco} #".center(60))
        print("=" * 60)
        print(f"  IQ Option: {tipo_conta_atual} ({saldo_api:.2f} {moeda_api})  |  BD Saldo Foco: {saldo_foco_db:.2f}")
        print("=" * 60)
        print("  Opções:")
        print(f"  1. Sincronizar Saldo {tipo_conta_foco} no BD")
        print(f"  2. Listar Ativos {mercado_foco}")
        print(f"  4. Trocar Tipo Conta (Sessão)")
        print(f"  5. Trocar Mercado (Sessão)")
        print(f"  6. Detalhes da Conta")
        print(f"  7. Configurar Payout Mínimo (Atual: {payout_minimo}%)")
        print(f"  8. Configurar Timeframe (Atual: {timeframe_padrao} min)")
        
        # Opções LSTM - Somente se disponível
        if LSTM_DISPONIVEL:
            print(f"\n[ Recursos LSTM ]")
            print(f"  9. Treinar Modelo LSTM")
            print(f"  10. Operação Automática com LSTM")
            print(f"  11. Análise de Predição LSTM")
            print(f"  12. Configurações LSTM")
            
        print("  0. Deslogar")
        
        escolha = input("\n  Escolha: ").strip()
        
        if escolha == "1":
            # Sincroniza saldo
            if tipo_conta_foco == tipo_conta_atual:
                atualizar_saldos_conta(conta_id, tipo_conta_foco, saldo_api, moeda_api)
                print(f"\n  ✅ Saldo {tipo_conta_foco} atualizado para {saldo_api} {moeda_api}")
            else:
                print(f"\n  ⚠️ Você está na conta {tipo_conta_atual}, mas quer atualizar {tipo_conta_foco}")
                confirma = input("  Deseja trocar para a conta desejada primeiro? (S/N): ").strip().upper()
                if confirma == "S":
                    # Trocar tipo de conta e depois sincroniza
                    if iq_session.trocar_tipo_conta(tipo_conta_foco):
                        novo_saldo = iq_session.api.get_balance()
                        nova_moeda = iq_session.api.get_currency()
                        atualizar_saldos_conta(conta_id, tipo_conta_foco, novo_saldo, nova_moeda)
                        print(f"\n  ✅ Saldo {tipo_conta_foco} atualizado para {novo_saldo} {nova_moeda}")
                    else:
                        print(f"\n  ❌ Não foi possível trocar para a conta {tipo_conta_foco}")
            
            press_enter_to_continue()
            
        elif escolha == "2":
            # Listar ativos e seus payouts
            ativos = exibir_ativos_abertos(iq_session, mercado_foco, payout_minimo, timeframe_padrao)
            # Não é necessário fazer nada com os ativos aqui, só exibir
            press_enter_to_continue()
            
        elif escolha == "4":
            # Trocar tipo de conta
            novo_tipo = selecionar_tipo_conta_interface(tipo_conta_foco)
            if novo_tipo != tipo_conta_foco:
                if iq_session.trocar_tipo_conta(novo_tipo):
                    print(f"\n  ✅ Tipo de conta alterado para {novo_tipo}")
                    tipo_conta_foco = novo_tipo
                else:
                    print(f"\n  ❌ Falha ao trocar tipo de conta")
                press_enter_to_continue()
                
        elif escolha == "5":
            # Trocar mercado foco
            novo_mercado = selecionar_mercado_ativo()
            if novo_mercado != mercado_foco:
                mercado_foco = novo_mercado
                print(f"\n  ✅ Mercado alterado para {mercado_foco}")
                press_enter_to_continue()
                
        elif escolha == "6":
            # Ver detalhes da conta
            info_api = {
                'tipo_conta': tipo_conta_atual,
                'saldo': saldo_api,
                'moeda': moeda_api
            }
            perfil_local = obter_perfil_conta_local(conta_id)
            exibir_detalhes_conta(info_api, saldos_db, perfil_local)
            press_enter_to_continue()
            
        elif escolha == "7":
            # Configurar payout mínimo
            print("\n" + "=" * 60)
            print("# CONFIGURAÇÃO DE PAYOUT MÍNIMO #".center(60))
            print("=" * 60)
            print(f"  Payout mínimo atual: {payout_minimo}%")
            print("  Digite o novo valor de payout mínimo (0-100):")
            print("  * Ativos com payout abaixo deste valor serão ignorados na análise")
            print("  * Valor recomendado: 85% ou maior")
            
            try:
                novo_payout = int(input("\n  Novo payout mínimo (%): ").strip())
                if 0 <= novo_payout <= 100:
                    payout_minimo = novo_payout
                    print(f"\n  ✅ Payout mínimo configurado para {payout_minimo}%")
                else:
                    print("\n  ❌ Valor inválido. Deve estar entre 0 e 100.")
            except ValueError:
                print("\n  ❌ Valor inválido. Digite apenas números.")
                
            press_enter_to_continue()
            
        elif escolha == "8":
            # Configurar timeframe
            print("\n" + "=" * 60)
            print("# CONFIGURAÇÃO DE TIMEFRAME #".center(60))
            print("=" * 60)
            print(f"  Timeframe atual: {timeframe_padrao} minutos")
            print("  Opções disponíveis:")
            print("  1 - 1 minuto (M1)")
            print("  5 - 5 minutos (M5)")
            print("  15 - 15 minutos (M15)")
            print("  30 - 30 minutos (M30)")
            print("  60 - 1 hora (H1)")
            print("  240 - 4 horas (H4)")
            
            try:
                novo_timeframe = int(input("\n  Novo timeframe (1, 5, 15, 30, 60, 240): ").strip())
                timeframes_validos = [1, 5, 15, 30, 60, 240]
                if novo_timeframe in timeframes_validos:
                    timeframe_padrao = novo_timeframe
                    print(f"\n  ✅ Timeframe configurado para {timeframe_padrao} minutos")
                else:
                    print("\n  ❌ Valor inválido. Escolha entre: 1, 5, 15, 30, 60 ou 240.")
            except ValueError:
                print("\n  ❌ Valor inválido. Digite apenas números.")
                
            press_enter_to_continue()
            
        # Opções LSTM - Somente se disponível
        elif LSTM_DISPONIVEL and escolha == "9":
            # Treinar modelo LSTM
            menu_treinar_modelo_lstm(iq_session, mercado_foco)
            press_enter_to_continue()
            
        elif LSTM_DISPONIVEL and escolha == "10":
            # Operação automática com LSTM
            menu_operacao_automatica_lstm(iq_session, mercado_foco)
            press_enter_to_continue()
            
        elif LSTM_DISPONIVEL and escolha == "11":
            # Análise de predição LSTM
            menu_analise_predicao_lstm(iq_session, mercado_foco)
            press_enter_to_continue()
            
        elif LSTM_DISPONIVEL and escolha == "12":
            # Configurações LSTM
            menu_configuracoes_lstm()
            press_enter_to_continue()
            
        elif escolha == "0":
            # Sair
            return False, tipo_conta_foco, mercado_foco
        else:
            print("\n  ❌ Opção inválida. Tente novamente.")
            time.sleep(1)
    
    return True, tipo_conta_foco, mercado_foco

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

# --- Funções de Menu LSTM --- #
def menu_treinar_modelo_lstm(iq_session, mercado_foco):
    """Interface para treinar modelo LSTM"""
    global timeframe_padrao, payout_minimo
    
    print_header("Treinamento de Modelo LSTM")
    
    # Verifica se existem modelos já treinados
    diretorio_modelos = "modelos"
    if not os.path.exists(diretorio_modelos):
        os.makedirs(diretorio_modelos)
        print("  Diretório de modelos criado.")
    
    modelos_existentes = [f for f in os.listdir(diretorio_modelos) if f.endswith('.keras')]
    
    print(f"  Mercado: {mercado_foco}")
    print(f"  Modelos existentes: {len(modelos_existentes)}")
    
    # Lista os ativos disponíveis para treinar usando a mesma função do menu principal
    ativos = exibir_ativos_abertos(iq_session, mercado_foco, payout_minimo, timeframe_padrao)
    
    if not ativos:
        print_error(f"Nenhum ativo disponível para {mercado_foco} com payout mínimo de {payout_minimo}%")
        return
    
    # Configurações de paginação
    itens_por_pagina = 10
    total_paginas = (len(ativos) + itens_por_pagina - 1) // itens_por_pagina
    pagina_atual = 1
    
    while True:
        inicio = (pagina_atual - 1) * itens_por_pagina
        fim = min(inicio + itens_por_pagina, len(ativos))
        
        # Selecionar o ativo para treinar
        print(f"\n  Selecione o ativo para treinar o modelo (Página {pagina_atual}/{total_paginas}):")
        
        # Exibir os ativos da página atual
        for i, (ativo, payout) in enumerate(ativos[inicio:fim], inicio + 1):
            print(f"    {i}. {ativo} (Payout: {payout if payout is not None else 'N/A'}%)")
        
        # Opções de navegação
        print("\n  Navegação:")
        if pagina_atual > 1:
            print("    A. Página anterior")
        if pagina_atual < total_paginas:
            print("    P. Próxima página")
        print("    0. Voltar ao menu principal")
        
        # Obter escolha do usuário
        escolha = input("\n  Escolha (número ou letra): ").strip().upper()
        
        # Verificar se é para voltar ao menu principal
        if escolha == "0":
            return
        
        # Verificar se é para navegar entre páginas
        if escolha == "A" and pagina_atual > 1:
            pagina_atual -= 1
            continue
        if escolha == "P" and pagina_atual < total_paginas:
            pagina_atual += 1
            continue
            
        # Verificar se é um número válido
        try:
            opcao = int(escolha)
            if 1 <= opcao <= len(ativos):
                ativo_selecionado = ativos[opcao-1][0]
                print(f"\n  ✅ Ativo selecionado: {ativo_selecionado}")
                
                # Confirmar treinamento
                print("\n  O treinamento pode levar vários minutos dependendo da quantidade de dados.")
                print("  Dica: Para melhor qualidade, use pelo menos 1000 velas históricas.")
                
                confirma = input("\n  Iniciar treinamento? (S/N): ").strip().upper()
                if confirma == "S":
                    print("\n  Iniciando treinamento do modelo LSTM...")
                    caminho_modelo = treinar_modelo(iq_session.api, ativo_selecionado, timeframe_padrao)
                    print(f"\n  ✅ Modelo treinado com sucesso: {caminho_modelo}")
                    return  # Retorna ao menu principal após o treinamento
                else:
                    print("\n  Treinamento cancelado.")
                    return  # Retorna ao menu principal
            else:
                print_error(f"Opção inválida. Digite um número entre 1 e {len(ativos)}.")
        except ValueError:
            print_error("Entrada inválida. Digite um número ou uma letra de navegação válida.")

def menu_operacao_automatica_lstm(iq_session, mercado_foco):
    """Interface para operação automática com LSTM"""
    global timeframe_padrao, payout_minimo
    
    print_header("Operação Automática LSTM")
    
    # Verificar se existem modelos treinados
    diretorio_modelos = "modelos"
    
    if not os.path.exists(diretorio_modelos):
        os.makedirs(diretorio_modelos)
    
    modelos_existentes = [f for f in os.listdir(diretorio_modelos) if f.endswith('.keras')]
    
    if not modelos_existentes:
        print_error("Nenhum modelo treinado encontrado. Treine um modelo primeiro.")
        return
    
    # Listar modelos disponíveis
    print("  Modelos disponíveis:")
    for i, modelo in enumerate(modelos_existentes, 1):
        print(f"    {i}. {modelo}")
    
    # Selecionar modelo
    try:
        opcao_modelo = int(input("\n  Selecione o modelo (número): "))
        if 1 <= opcao_modelo <= len(modelos_existentes):
            modelo_selecionado = os.path.join(diretorio_modelos, modelos_existentes[opcao_modelo-1])
            print(f"\n  ✅ Modelo selecionado: {modelos_existentes[opcao_modelo-1]}")
        else:
            print_error("Opção inválida.")
            return
    except ValueError:
        print_error("Entrada inválida. Digite um número.")
        return
    
    # Lista os ativos disponíveis para operar usando a mesma função do menu principal
    ativos = exibir_ativos_abertos(iq_session, mercado_foco, payout_minimo, timeframe_padrao)
    
    if not ativos:
        print_error(f"Nenhum ativo disponível para {mercado_foco} com payout mínimo de {payout_minimo}%")
        return
    
    # Configurações de paginação
    itens_por_pagina = 10
    total_paginas = (len(ativos) + itens_por_pagina - 1) // itens_por_pagina
    pagina_atual = 1
    
    while True:
        inicio = (pagina_atual - 1) * itens_por_pagina
        fim = min(inicio + itens_por_pagina, len(ativos))
        
        # Exibir os ativos da página atual
        print(f"\n  Selecione o ativo para operar (Página {pagina_atual}/{total_paginas}):")
        for i, (ativo, payout) in enumerate(ativos[inicio:fim], inicio + 1):
            print(f"    {i}. {ativo} (Payout: {payout if payout is not None else 'N/A'}%)")
        
        # Opções de navegação
        print("\n  Navegação:")
        if pagina_atual > 1:
            print("    A. Página anterior")
        if pagina_atual < total_paginas:
            print("    P. Próxima página")
        print("    0. Voltar ao menu principal")
        
        # Obter escolha do usuário
        escolha = input("\n  Escolha (número ou letra): ").strip().upper()
        
        # Verificar se é para voltar ao menu principal
        if escolha == "0":
            return
        
        # Verificar se é para navegar entre páginas
        if escolha == "A" and pagina_atual > 1:
            pagina_atual -= 1
            continue
        if escolha == "P" and pagina_atual < total_paginas:
            pagina_atual += 1
            continue
            
        # Verificar se é um número válido
        try:
            opcao = int(escolha)
            if 1 <= opcao <= len(ativos):
                ativo_selecionado = ativos[opcao-1][0]
                print(f"\n  ✅ Ativo selecionado: {ativo_selecionado}")
                
                # Perguntar o valor para entrada
                try:
                    valor_entrada = float(input("\n  Valor da entrada: $"))
                    if valor_entrada <= 0:
                        print_error("O valor deve ser maior que zero.")
                        continue
                except ValueError:
                    print_error("Entrada inválida. Digite um número válido.")
                    continue
                
                # Perguntar quantas operações realizar
                try:
                    quantidade_operacoes = int(input("\n  Quantidade de operações (1-100): "))
                    if not 1 <= quantidade_operacoes <= 100:
                        print_error("A quantidade deve estar entre 1 e 100.")
                        continue
                except ValueError:
                    print_error("Entrada inválida. Digite um número inteiro.")
                    continue
                
                # Confirmar início das operações
                print("\n\n  ⚠️ ATENÇÃO: Você está prestes a iniciar operações reais.")
                print(f"  Serão executadas até {quantidade_operacoes} operações de ${valor_entrada} no ativo {ativo_selecionado}.")
                
                confirmacao = input("\n  Confirma o início das operações? (S/N): ").strip().upper()
                if confirmacao != 'S':
                    print("\n  Operações canceladas pelo usuário.")
                    return
                
                # Executar operações
                print("\n  Iniciando operações automáticas...")
                print("  Pressione Ctrl+C a qualquer momento para interromper.\n")
                
                try:
                    resultado = executar_operacoes_lstm(
                        iq_session.api, 
                        modelo_selecionado, 
                        ativo_selecionado, 
                        valor_entrada, 
                        quantidade_operacoes
                    )
                    
                    # Verificar se tivemos erro
                    if isinstance(resultado, dict) and resultado.get('erro', False):
                        print_error(f"{resultado.get('mensagem', 'Erro ao executar operações automáticas.')}")
                        
                        # Orientações adicionais baseadas no tipo de erro
                        tipo_erro = resultado.get('tipo_erro')
                        if tipo_erro == 'arquivo_nao_encontrado':
                            print("  Você precisa treinar um modelo LSTM primeiro antes de fazer operações.")
                            print("  Use a opção 'Treinar Modelo LSTM' no menu principal.")
                        elif tipo_erro == 'modelo_corrompido':
                            print("  O arquivo de modelo parece estar corrompido ou em formato inválido.")
                            print("  Sugestão: Tente treinar novamente o modelo com a opção 'Treinar Modelo LSTM'.")
                            print("  Se o problema persistir, verifique se há erros durante o treinamento.")
                    else:
                        # Mostrar resumo das operações
                        print("\n  Resumo das operações:")
                        print(f"  - Total de operações: {resultado.get('total_operacoes', 0)}")
                        print(f"  - Ganhos: {resultado.get('wins', 0)}")
                        print(f"  - Perdas: {resultado.get('losses', 0)}")
                        print(f"  - Empates: {resultado.get('ties', 0)}")
                        
                        # Calcular taxa de acerto
                        if resultado.get('total_operacoes', 0) > 0:
                            taxa_acerto = (resultado.get('wins', 0) / resultado.get('total_operacoes', 0)) * 100
                            print(f"  - Taxa de acerto: {taxa_acerto:.2f}%")
                        
                        print("\n  ✅ Operações automáticas concluídas!")
                    
                except KeyboardInterrupt:
                    print("\n\n  ⚠️ Operações interrompidas pelo usuário.")
                except Exception as e:
                    logging.error(f"Erro durante operações automáticas: {str(e)}")
                    print_error(f"Erro durante operações automáticas: {str(e)}")
                
                # Aguardar confirmação para voltar ao menu
                input("\n  Pressione Enter para voltar ao menu principal...")
                return
            else:
                print_error(f"Opção inválida. Digite um número entre 1 e {len(ativos)}.")
        except ValueError:
            print_error("Entrada inválida. Digite um número ou uma letra de navegação válida.")

def menu_analise_predicao_lstm(iq_session, mercado_foco):
    """Interface para análise de predição com LSTM"""
    global timeframe_padrao, payout_minimo
    
    print_header("Análise de Predição LSTM")
    
    # Verificar se existem modelos treinados
    diretorio_modelos = "modelos"
    modelos_existentes = [f for f in os.listdir(diretorio_modelos) if f.endswith('.keras')]
    
    if not modelos_existentes:
        print_error("Nenhum modelo treinado encontrado. Treine um modelo primeiro.")
        return
    
    # Listar modelos disponíveis
    print("  Modelos disponíveis:")
    for i, modelo in enumerate(modelos_existentes, 1):
        print(f"    {i}. {modelo}")
    
    # Selecionar modelo
    try:
        opcao_modelo = int(input("\n  Selecione o modelo (número): "))
        if 1 <= opcao_modelo <= len(modelos_existentes):
            modelo_selecionado = os.path.join(diretorio_modelos, modelos_existentes[opcao_modelo-1])
            print(f"\n  ✅ Modelo selecionado: {modelos_existentes[opcao_modelo-1]}")
        else:
            print_error("Opção inválida.")
            return
    except ValueError:
        print_error("Entrada inválida. Digite um número.")
        return
    
    # Lista os ativos disponíveis para análise usando a mesma função do menu principal
    ativos = exibir_ativos_abertos(iq_session, mercado_foco, payout_minimo, timeframe_padrao)
    
    if not ativos:
        print_error(f"Nenhum ativo disponível para {mercado_foco} com payout mínimo de {payout_minimo}%")
        return
    
    # Configurações de paginação
    itens_por_pagina = 10
    total_paginas = (len(ativos) + itens_por_pagina - 1) // itens_por_pagina
    pagina_atual = 1
    
    while True:
        inicio = (pagina_atual - 1) * itens_por_pagina
        fim = min(inicio + itens_por_pagina, len(ativos))
        
        # Exibir os ativos da página atual
        print(f"\n  Selecione o ativo para análise (Página {pagina_atual}/{total_paginas}):")
        for i, (ativo, payout) in enumerate(ativos[inicio:fim], inicio + 1):
            print(f"    {i}. {ativo} (Payout: {payout if payout is not None else 'N/A'}%)")
        
        # Opções de navegação
        print("\n  Navegação:")
        if pagina_atual > 1:
            print("    A. Página anterior")
        if pagina_atual < total_paginas:
            print("    P. Próxima página")
        print("    0. Voltar ao menu principal")
        
        # Obter escolha do usuário
        escolha = input("\n  Escolha (número ou letra): ").strip().upper()
        
        # Verificar se é para voltar ao menu principal
        if escolha == "0":
            return
        
        # Verificar se é para navegar entre páginas
        if escolha == "A" and pagina_atual > 1:
            pagina_atual -= 1
            continue
        if escolha == "P" and pagina_atual < total_paginas:
            pagina_atual += 1
            continue
            
        # Verificar se é um número válido
        try:
            opcao = int(escolha)
            if 1 <= opcao <= len(ativos):
                ativo_selecionado = ativos[opcao-1][0]
                print(f"\n  ✅ Ativo selecionado: {ativo_selecionado}")
                
                # Executar análise
                print("\n  Analisando dados e gerando predição...")
                resultado = analisar_ativo_lstm(iq_session.api, modelo_selecionado, ativo_selecionado)
                
                # Verificar se tivemos erro
                if resultado is None:
                    print_error("Falha na análise. Verifique os logs para mais detalhes.")
                    continue
                
                # Mostrar resultados
                if resultado.get('erro', False):
                    print_error(f"{resultado.get('mensagem', 'Erro na análise do ativo.')}")
                    
                    # Orientações adicionais baseadas no tipo de erro
                    tipo_erro = resultado.get('tipo_erro')
                    if tipo_erro == 'arquivo_nao_encontrado':
                        print("  Você precisa treinar um modelo LSTM primeiro antes de fazer análises.")
                        print("  Use a opção 'Treinar Modelo LSTM' no menu principal.")
                    elif tipo_erro == 'modelo_corrompido':
                        print("  O arquivo de modelo parece estar corrompido ou em formato inválido.")
                        print("  Sugestão: Tente treinar novamente o modelo com a opção 'Treinar Modelo LSTM'.")
                        print("  Se o problema persistir, verifique se há erros durante o treinamento.")
                else:
                    direcao = "ALTA (CALL)" if resultado['direcao'] == 'call' else "BAIXA (PUT)"
                    confianca = resultado['confianca']
                    
                    print("\n  Resultado da análise:")
                    print(f"  - Ativo: {ativo_selecionado}")
                    print(f"  - Previsão: {direcao}")
                    print(f"  - Confiança: {confianca:.2f}%")
                    print(f"  - Modelo utilizado: {resultado.get('modelo', 'N/A')}")
                    
                    # Mostrar indicadores técnicos adicionais
                    if 'indicadores' in resultado and resultado['indicadores']:
                        print("\n  Indicadores técnicos:")
                        for nome, valor in resultado['indicadores'].items():
                            print(f"  - {nome}: {valor}")
                    else:
                        print("\n  Não foi possível calcular indicadores técnicos adicionais.")
                
                # Perguntar se deseja analisar outro ativo
                continuar = input("\n  Analisar outro ativo? (S/N): ").strip().upper()
                if continuar != 'S':
                    return
                break  # Sai do loop atual para reiniciar a seleção de ativo
            else:
                print_error(f"Opção inválida. Digite um número entre 1 e {len(ativos)}.")
        except ValueError:
            print_error("Entrada inválida. Digite um número ou uma letra de navegação válida.")

def menu_configuracoes_lstm():
    """Interface para configurar parâmetros LSTM"""
    print_header("Configurações LSTM")
    
    # Definir caminhos dos arquivos de configuração
    config_dir = "configuracoes"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    config_path = os.path.join(config_dir, "lstm_config.ini")
    
    # Configurações padrão
    config_padrao = {
        'seq_len': 5,
        'future_predict': 2,
        'batch_size': 16,
        'epochs': 40,
        'learning_rate': 0.001
    }
    
    # Carregar configurações atuais ou usar padrão
    import configparser
    config = configparser.ConfigParser()
    
    if os.path.exists(config_path):
        config.read(config_path)
        if 'LSTM' not in config:
            config['LSTM'] = {}
        
        current_config = {
            'seq_len': config['LSTM'].getint('seq_len', config_padrao['seq_len']),
            'future_predict': config['LSTM'].getint('future_predict', config_padrao['future_predict']),
            'batch_size': config['LSTM'].getint('batch_size', config_padrao['batch_size']),
            'epochs': config['LSTM'].getint('epochs', config_padrao['epochs']),
            'learning_rate': config['LSTM'].getfloat('learning_rate', config_padrao['learning_rate'])
        }
    else:
        current_config = config_padrao
        config['LSTM'] = {}
    
    # Mostrar configurações atuais
    print("  Configurações atuais:")
    print(f"  1. Tamanho da sequência (SEQ_LEN): {current_config['seq_len']}")
    print(f"  2. Períodos futuros para previsão: {current_config['future_predict']}")
    print(f"  3. Tamanho do lote (BATCH_SIZE): {current_config['batch_size']}")
    print(f"  4. Épocas de treinamento: {current_config['epochs']}")
    print(f"  5. Taxa de aprendizado: {current_config['learning_rate']}")
    print("  0. Salvar e voltar")
    
    # Menu para alteração de parâmetros
    while True:
        opcao = input("\n  Escolha o parâmetro para alterar (0-5): ").strip()
        
        if opcao == "0":
            # Salvar configurações
            for key, value in current_config.items():
                config['LSTM'][key] = str(value)
            
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            
            print_success("Configurações salvas com sucesso!")
            break
        
        elif opcao == "1":
            try:
                valor = int(input(f"  Novo valor para SEQ_LEN (atual: {current_config['seq_len']}): "))
                if valor > 0:
                    current_config['seq_len'] = valor
                    print(f"  ✅ SEQ_LEN alterado para {valor}")
                else:
                    print_error("Valor deve ser maior que zero.")
            except ValueError:
                print_error("Entrada inválida. Digite um número inteiro.")
        
        elif opcao == "2":
            try:
                valor = int(input(f"  Novo valor para previsão futura (atual: {current_config['future_predict']}): "))
                if valor > 0:
                    current_config['future_predict'] = valor
                    print(f"  ✅ Períodos futuros alterado para {valor}")
                else:
                    print_error("Valor deve ser maior que zero.")
            except ValueError:
                print_error("Entrada inválida. Digite um número inteiro.")
        
        elif opcao == "3":
            try:
                valor = int(input(f"  Novo valor para BATCH_SIZE (atual: {current_config['batch_size']}): "))
                if valor > 0:
                    current_config['batch_size'] = valor
                    print(f"  ✅ BATCH_SIZE alterado para {valor}")
                else:
                    print_error("Valor deve ser maior que zero.")
            except ValueError:
                print_error("Entrada inválida. Digite um número inteiro.")
        
        elif opcao == "4":
            try:
                valor = int(input(f"  Novo valor para épocas (atual: {current_config['epochs']}): "))
                if valor > 0:
                    current_config['epochs'] = valor
                    print(f"  ✅ Épocas alterado para {valor}")
                else:
                    print_error("Valor deve ser maior que zero.")
            except ValueError:
                print_error("Entrada inválida. Digite um número inteiro.")
        
        elif opcao == "5":
            try:
                valor = float(input(f"  Novo valor para taxa de aprendizado (atual: {current_config['learning_rate']}): "))
                if valor > 0:
                    current_config['learning_rate'] = valor
                    print(f"  ✅ Taxa de aprendizado alterado para {valor}")
                else:
                    print_error("Valor deve ser maior que zero.")
            except ValueError:
                print_error("Entrada inválida. Digite um número decimal.")
        
        else:
            print_error("Opção inválida.")

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