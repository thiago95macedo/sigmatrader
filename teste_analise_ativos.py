#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de teste para o módulo de análise de ativos da IQ Option
Implementa mecanismos de reconexão e pausas para evitar problemas de conexão
"""

import os
import sys
import time
import logging
import getpass
from datetime import datetime

from iqoption.login import LoginIQOption
from iqoption.analisador_ativos import interface_analise_ativos

# Configurações de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("teste_analise_ativos.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Silenciar logs de bibliotecas de terceiros
logging.getLogger('iqoptionapi.ws.client').setLevel(logging.WARNING)
logging.getLogger('iqoptionapi.api').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('websocket').setLevel(logging.WARNING)

def executar_analise_ativos(email, senha, mercado="Binário/Turbo"):
    """
    Executa a análise de ativos com tratamento de erros e reconexão
    
    Args:
        email: Email da conta IQ Option
        senha: Senha da conta IQ Option
        mercado: Tipo de mercado para análise (padrão: Binário/Turbo)
        
    Returns:
        bool: True se a análise foi concluída com sucesso, False caso contrário
    """
    print(f"\n{'=' * 50}")
    print(f"TESTE DO ANALISADOR DE ATIVOS - MERCADO {mercado}".center(50))
    print(f"{'=' * 50}\n")
    
    print(f"Conectando à IQ Option com email: {email}")
    
    # Tenta conectar à IQ Option
    login_manager = LoginIQOption()
    sucesso_conexao = login_manager.conectar(email, senha, "TREINAMENTO")
    
    if not sucesso_conexao:
        print(f"❌ Falha na conexão à IQ Option. Verifique suas credenciais.")
        return False
    
    print(f"✅ Conexão estabelecida com sucesso!")
    print(f"   Tipo de conta: {login_manager.api.get_balance_mode()}")
    print(f"   Saldo: {login_manager.api.get_balance()} {login_manager.api.get_currency()}")
    
    # Função de callback para atualizar progresso
    def mostrar_progresso(percentual, mensagem=""):
        barra = "█" * int(percentual / 2) + "░" * (50 - int(percentual / 2))
        print(f"\r[{barra}] {percentual:.1f}% {mensagem}", end="", flush=True)
        if percentual >= 100:
            print()  # Nova linha quando completo
    
    try:
        print("\nIniciando análise de ativos...")
        print("Coletando até 1000 velas por ativo (máximo permitido pela API)...")
        start_time = time.time()
        
        # Executar análise
        df_metricas, caminho_html = interface_analise_ativos(
            login_manager.api, 
            mercado, 
            mostrar_progresso
        )
        
        # Tempo total
        tempo_total = time.time() - start_time
        
        if df_metricas is not None and not df_metricas.empty:
            print(f"\n✅ Análise concluída com sucesso em {tempo_total:.1f} segundos!")
            print(f"   Ativos analisados: {len(df_metricas)}")
            
            # Mostrar top 5 ativos
            print("\nTop 5 ativos recomendados:")
            for i, (ativo, row) in enumerate(df_metricas.head(5).iterrows(), 1):
                print(f"   {i}. {ativo} - Payout: {row['payout']*100:.0f}%, " +
                      f"Volatilidade: {row['volatilidade_nome']}, " +
                      f"Tendência: {row['tendencia_nome']}, " +
                      f"Pontuação: {row['pontuacao']:.2f}")
            
            # Informações sobre o relatório HTML
            if caminho_html:
                print(f"\nRelatório HTML salvo em: {caminho_html}")
                
                # Em sistemas Unix, tenta abrir o relatório no navegador
                if os.name == "posix":
                    try:
                        import webbrowser
                        webbrowser.open(f"file://{os.path.abspath(caminho_html)}")
                        print("Relatório aberto no navegador.")
                    except:
                        pass
            
            return True
        else:
            print(f"\n❌ Falha na análise de ativos. Veja o log para mais detalhes.")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Análise interrompida pelo usuário.")
        return False
        
    except Exception as e:
        print(f"\n❌ Erro durante a análise: {str(e)}")
        logger.exception("Erro na execução do teste de análise de ativos")
        return False
    
    finally:
        # Sempre tenta desconectar
        try:
            print("\nDesconectando da IQ Option...")
            login_manager.api.logout()
            print("✅ Desconectado com sucesso!")
        except:
            print("⚠️ Não foi possível desconectar corretamente.")

if __name__ == "__main__":
    # Tenta obter credenciais de ambiente ou argumentos
    email = os.environ.get("IQ_EMAIL", None)
    senha = os.environ.get("IQ_PASSWORD", None)
    
    # Se não encontrar no ambiente, pede ao usuário
    if not email:
        if len(sys.argv) > 1:
            email = sys.argv[1]
        else:
            email = input("Email IQ Option: ").strip()
    
    if not senha:
        if len(sys.argv) > 2:
            senha = sys.argv[2]
        else:
            senha = getpass.getpass("Senha IQ Option: ")
    
    # Seleciona o mercado
    print("\nSelecione o mercado para análise:")
    print("1. Binário/Turbo (padrão)")
    print("2. Digital")
    print("3. Forex")
    print("4. Cripto")
    
    opcao = input("Opção (1-4): ").strip() or "1"
    
    mercados = {
        "1": "Binário/Turbo",
        "2": "Digital",
        "3": "Forex",
        "4": "Cripto"
    }
    
    mercado_selecionado = mercados.get(opcao, "Binário/Turbo")
    
    # Executa análise
    executar_analise_ativos(email, senha, mercado_selecionado) 