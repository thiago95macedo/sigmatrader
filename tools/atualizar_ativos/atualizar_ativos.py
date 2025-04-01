#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para atualizar os códigos dos ativos da IQ Option
Data: 31/03/2025
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option

# Configuração de logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Credenciais (substitua por suas credenciais reais)
EMAIL = "thiago95macedo@gmail.com"
SENHA = "@TGM95@manakel"

# Obtém o diretório onde este script está localizado
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho do arquivo constants.py original
CONSTANTS_PATH = "dependencias/iqoptionapi/iqoptionapi/constants.py"
# Caminho da pasta da API
API_PATH = "dependencias/iqoptionapi"

def obter_ativos():
    """Conecta à API da IQ Option e obtém os ativos disponíveis"""
    
    logger.info("Iniciando conexão com a IQ Option")
    api = IQ_Option(EMAIL, SENHA)
    
    # Tenta conectar
    status, motivo = api.connect()
    if not status:
        logger.error(f"Erro ao conectar: {motivo}")
        return None
    
    # Verifica se está conectado
    if api.check_connect():
        logger.info("Conectado com sucesso à IQ Option")
    else:
        logger.error("Falha na conexão")
        return None
    
    # Obtém os ativos disponíveis usando get_all_open_time
    logger.info("Obtendo lista de ativos disponíveis...")
    ativos_abertos = api.get_all_open_time()
    
    if not ativos_abertos:
        logger.error("Não foi possível obter a lista de ativos")
        return None
    
    # Extrai os nomes dos ativos e associa opcodes (se disponíveis)
    ativos = {}
    for tipo, dados in ativos_abertos.items():
        for ativo in dados.keys():
            # Placeholder para o opcode (ainda não obtido diretamente)
            ativos[ativo] = 0  # Substitua por lógica para obter o opcode, se disponível
    
    logger.info(f"Foram encontrados {len(ativos)} ativos")
    
    # Salva os dados em um arquivo JSON no mesmo diretório do script
    data_atual = datetime.now().strftime("%Y%m%d")
    nome_arquivo = os.path.join(SCRIPT_DIR, f"ativos_iqoption_{data_atual}.json")
    
    with open(nome_arquivo, 'w') as f:
        json.dump(ativos, f, indent=4, sort_keys=True)
    
    logger.info(f"Dados salvos em {nome_arquivo}")
    
    # Gera o código Python para constants.py
    gerar_constants_py(ativos)
    
    return ativos

def gerar_constants_py(ativos):
    """Gera o código Python para atualizar constants.py"""
    
    codigo = '''"""
"Module for IQ Option API constants."
"""

# Códigos de ativos da IQ Option atualizados
# Gerado automaticamente em {data}
ACTIVES = {{
{conteudo}
}}

# Mapeamento reverso para obter o nome do ativo a partir do código
ACTIVES_CODES = {{v: k for k, v in ACTIVES.items()}}

# Tipos de instrumentos
INSTRUMENT_TYPES = {{
    "forex": "forex",
    "cfd": "cfd", 
    "crypto": "crypto",
}}

# Tipos de opções
OPTION_TYPES = {{
    "binary": "turbo",
    "turbo": "turbo",
    "digital": "digital",
}}
'''.format(
        data=datetime.now().strftime("%d/%m/%Y"),
        conteudo='\n'.join([f'\t"{ativo}": {id_ativo},' for ativo, id_ativo in sorted(ativos.items())])
    )
    
    # Salva o arquivo constants_atualizado.py no mesmo diretório do script
    constants_atualizado_path = os.path.join(SCRIPT_DIR, "constants_atualizado.py")
    with open(constants_atualizado_path, 'w') as f:
        f.write(codigo)
    
    logger.info(f"Arquivo constants_atualizado.py gerado com sucesso em {constants_atualizado_path}")
    
    # Converte o caminho relativo para absoluto para o constants.py original
    constants_path_abs = os.path.join(os.path.dirname(SCRIPT_DIR), "..", CONSTANTS_PATH)
    
    # Atualiza o arquivo constants.py original
    if os.path.exists(constants_path_abs):
        # Faz um backup do arquivo original
        backup_path = f"{constants_path_abs}.backup"
        try:
            with open(constants_path_abs, 'r') as original:
                conteudo_original = original.read()
                
            with open(backup_path, 'w') as backup:
                backup.write(conteudo_original)
                
            logger.info(f"Backup do arquivo original criado em {backup_path}")
            
            # Atualiza o arquivo original
            with open(constants_path_abs, 'w') as original:
                original.write(codigo)
                
            logger.info(f"Arquivo {constants_path_abs} atualizado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao atualizar arquivo original: {e}")
    else:
        logger.warning(f"Arquivo {constants_path_abs} não encontrado. Não foi possível atualizá-lo automaticamente.")
        logger.info(f"Para atualizar manualmente, copie constants_atualizado.py para {constants_path_abs}")

def atualizar_api_via_pip():
    """Atualiza a API iqoptionapi via pip"""
    logger.info("Iniciando atualização da API via pip...")
    
    # Converte o caminho relativo para absoluto para a pasta da API
    api_path_abs = os.path.join(os.path.dirname(SCRIPT_DIR), "..", API_PATH)
    
    if not os.path.exists(api_path_abs):
        logger.error(f"Diretório da API não encontrado: {api_path_abs}")
        return False
    
    try:
        # Executa o comando pip para reinstalar o pacote a partir do diretório local
        comando = f"pip install -e {api_path_abs} --force-reinstall"
        logger.info(f"Executando comando: {comando}")
        
        processo = subprocess.run(
            comando,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("Saída do comando pip:")
        for linha in processo.stdout.split('\n'):
            if linha.strip():
                logger.info(linha.strip())
        
        logger.info("API atualizada com sucesso via pip!")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao atualizar API via pip: {e}")
        logger.error(f"Erro detalhado: {e.stderr}")
        return False
    
    except Exception as e:
        logger.error(f"Erro inesperado durante atualização da API: {e}")
        return False

def main():
    """Função principal"""
    try:
        ativos = obter_ativos()
        if ativos:
            logger.info("Ativos atualizados com sucesso")
            
            # Atualiza a API via pip
            if atualizar_api_via_pip():
                logger.info("Processo completo: ativos e API atualizados com sucesso")
            else:
                logger.warning("Os ativos foram atualizados, mas houve um problema ao atualizar a API")
        else:
            logger.error("Não foi possível obter os ativos")
    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
    finally:
        logger.info("Finalizando execução...")

if __name__ == "__main__":
    main()