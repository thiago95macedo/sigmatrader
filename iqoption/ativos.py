#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para obter informações sobre ativos da IQ Option API
"""

import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Mapeamento de tipos de interesse e seus nomes amigáveis
TIPOS_INTERESSE = {
    "digital": "Digital",
    "binary": "Binário/Turbo", # Agrupa os dois
    "turbo": "Binário/Turbo",
    "forex": "Forex",
    "crypto": "Cripto",
    # Adicione outros tipos se necessário (cfd, stocks)
}

# Mapeamento reverso de nome amigável para tipos da API (para filtragem)
MERCADO_PARA_TIPOS_API = {
    "Digital": ["digital"],
    "Binário/Turbo": ["binary", "turbo"],
    "Forex": ["forex"],
    "Cripto": ["crypto"],
}

def listar_ativos_abertos(api, mercado_foco=None):
    """
    Obtém e filtra os ativos abertos para negociação na IQ Option.
    Pode filtrar por um mercado específico (Digital, Binário/Turbo, Forex, Cripto).
    
    Parâmetros:
        api: Instância conectada da IQ_Option API.
        mercado_foco (str, optional): O mercado específico a ser listado 
                                      (ex: "Digital", "Binário/Turbo"). 
                                      Se None, lista todos os tipos de interesse.
        
    Retorna:
        dict: Dicionário onde as chaves são os nomes amigáveis dos tipos 
              e os valores são listas de nomes de ativos abertos, ou None em caso de erro.
              Se mercado_foco for especificado, o dict conterá apenas essa chave.
    """
    if not api or not api.check_connect():
        logger.error("API não conectada. Não é possível obter ativos abertos.")
        return None
        
    logger.info(f"Obtendo todos os ativos abertos da IQ Option... Foco: {mercado_foco or 'Todos'}")
    try:
        ativos_raw = api.get_all_open_time()
    except Exception as e:
        logger.error(f"Erro ao chamar api.get_all_open_time(): {e}", exc_info=True)
        return None
        
    if not ativos_raw:
        logger.warning("Nenhum dado de ativos abertos retornado pela API.")
        return {}
        
    # Define os tipos da API a serem considerados com base no foco
    tipos_api_considerar = []
    if mercado_foco:
        tipos_api_considerar = MERCADO_PARA_TIPOS_API.get(mercado_foco, [])
    else:
        # Se sem foco, considera todos os tipos mapeados em TIPOS_INTERESSE
        tipos_api_considerar = list(TIPOS_INTERESSE.keys())

    if not tipos_api_considerar:
        logger.warning(f"Mercado foco '{mercado_foco}' não reconhecido ou sem tipos de API mapeados.")
        return {}

    ativos_filtrados = {}
    # Inicializa o dicionário apenas com o mercado_foco se houver um
    if mercado_foco:
        ativos_filtrados[mercado_foco] = []
    else:
        # Inicializa com todos os nomes amigáveis mapeados
        for nome_amigavel in set(TIPOS_INTERESSE.values()):
            ativos_filtrados[nome_amigavel] = []

    logger.info("Filtrando ativos por tipo...")
    ativos_ja_adicionados = set() # Para evitar duplicatas ao agrupar Binário/Turbo
    
    # Processa os tipos retornados pela API
    for tipo_api, data_tipo in ativos_raw.items():
        if not isinstance(data_tipo, dict):
            continue 
            
        tipo_api_lower = tipo_api.lower()
        
        # Verifica se este tipo_api deve ser considerado com base no foco
        if tipo_api_lower in tipos_api_considerar:
            # Determina a chave de destino no dicionário filtrado
            chave_destino = TIPOS_INTERESSE.get(tipo_api_lower) 
            if not chave_destino: continue # Segurança extra

            # Adiciona os ativos abertos
            ativos_abertos_tipo = [ativo for ativo, status in data_tipo.items() if isinstance(status, dict) and status.get('open', False)]
            
            if ativos_abertos_tipo:
                 # Garante que a chave de destino existe (deveria existir pela inicialização)
                if chave_destino not in ativos_filtrados:
                    ativos_filtrados[chave_destino] = [] 
                
                # Adiciona ativos à lista, evitando duplicatas para Binário/Turbo
                for ativo in sorted(ativos_abertos_tipo):
                    identificador_unico = f"{chave_destino}|{ativo}"
                    if identificador_unico not in ativos_ja_adicionados:
                        ativos_filtrados[chave_destino].append(ativo)
                        ativos_ja_adicionados.add(identificador_unico)
                        
    # Remove categorias que ficaram vazias (importante se não houver foco)
    ativos_finais = {k: sorted(v) for k, v in ativos_filtrados.items() if v}
    
    log_info = {k: len(v) for k, v in ativos_finais.items()}
    logger.info(f"Ativos abertos filtrados ({mercado_foco or 'Todos'}): {log_info}")
    
    return ativos_finais 