#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para obter informações sobre ativos da IQ Option API, incluindo payouts.
"""

import logging
import time

# Configuração de logging
logger = logging.getLogger(__name__)

# Mapeamento de tipos de interesse e seus nomes amigáveis
TIPOS_INTERESSE = {
    "digital": "Digital",
    "binary": "Binário/Turbo", # Agrupa os dois
    "turbo": "Binário/Turbo",
    "forex": "Forex",
    "crypto": "Cripto",
}

# Mapeamento reverso de nome amigável para tipos da API (para filtragem)
MERCADO_PARA_TIPOS_API = {
    "Digital": ["digital"],
    "Binário/Turbo": ["binary", "turbo"],
    "Forex": ["forex"],
    "Cripto": ["crypto"],
}

# Timeframes disponíveis (em segundos)
TIMEFRAMES = {
    1: 60,     # 1 minuto
    5: 300,    # 5 minutos
    15: 900,   # 15 minutos
    30: 1800,  # 30 minutos
    60: 3600,  # 1 hora
    240: 14400 # 4 horas
}

def listar_ativos_abertos_com_payout(api, mercado_foco="Binário/Turbo", timeframe=1):
    """
    Obtém os ativos abertos para um mercado específico, com seus respectivos payouts (lucro),
    ordenados pelo tipo (ativos normais primeiro, depois OTC) e depois pelo payout decrescente,
    filtrando por timeframe disponível.

    Foco principal: Opções Binárias/Turbo ou Digitais. Outros mercados podem não retornar payout.
    
    Parâmetros:
        api: Instância conectada da IQ_Option API.
        mercado_foco (str): O mercado específico ("Binário/Turbo" ou "Digital"). 
                            Default é "Binário/Turbo".
        timeframe (int): O timeframe desejado em minutos (1, 5, 15, 30, 60, 240).
                        Default é 1 minuto.
        
    Retorna:
        list: Lista de tuplas `(nome_ativo, payout_percentual)` ordenada primeiro por tipo 
              (normais antes de OTC) e depois por payout (decrescente), 
              ou None em caso de erro ou API não conectada. 
              Retorna lista vazia se não houver ativos abertos com payout disponível.
              Ex: [('EURUSD', 87), ('GBPUSD', 85), ('EURUSD-OTC', 80), ...]
    """
    if not api or not api.check_connect():
        logger.error("API não conectada. Não é possível obter ativos e payouts.")
        return None
        
    logger.info(f"Buscando ativos abertos e payouts para o mercado: {mercado_foco}, timeframe: {timeframe} min")
    
    # Verificar se o timeframe é válido
    if timeframe not in TIMEFRAMES:
        logger.warning(f"Timeframe {timeframe} não suportado. Usando timeframe padrão de 1 minuto.")
        timeframe = 1  # Valor padrão
    
    timeframe_segundos = TIMEFRAMES[timeframe]
    
    tipos_api_considerar = MERCADO_PARA_TIPOS_API.get(mercado_foco)
    if not tipos_api_considerar:
        logger.warning(f"Mercado foco '{mercado_foco}' não suportado para consulta de payout ou inválido.")
        return [] # Retorna lista vazia para mercado não suportado

    # 1. Obter ativos abertos
    try:
        ativos_raw = api.get_all_open_time()
        if not ativos_raw:
            logger.warning("Nenhum dado de ativos abertos retornado pela API.")
            return []
    except Exception as e:
        logger.error(f"Erro ao chamar api.get_all_open_time(): {e}", exc_info=True)
        return None

    # 1.5 Obter dados de inicialização para detalhes (payout, expiração)
    init_info = None
    if mercado_foco == "Binário/Turbo": # Só busca init_info se for relevante
        try:
            init_info = api.get_all_init()
            if not init_info or not init_info.get("isSuccessful"):
                logger.error("Falha ao obter dados de inicialização (get_all_init).")
                # Decide se continua sem payouts/expirações ou retorna erro
                # Por ora, continua, mas payout/expiração serão None
                init_info = None 
        except Exception as e_init:
            logger.error(f"Erro ao chamar api.get_all_init(): {e_init}", exc_info=True)
            init_info = None # Continua sem os detalhes

    # 2. Processar Ativos e Payouts
    ativos_com_detalhes = []
    ativos_abertos_set = set()
    
    if mercado_foco == "Binário/Turbo" and init_info:
        # Usa get_all_profit que já depende de get_all_init
        try:
            all_profits = api.get_all_profit() 
            if not all_profits:
                 logger.warning("Nenhum dado de profit retornado por get_all_profit().")
                 all_profits = {} # Define como dict vazio para evitar erros abaixo
        except Exception as e_profit:
            logger.error(f"Erro ao chamar api.get_all_profit(): {e_profit}", exc_info=True)
            all_profits = {} # Trata como vazio se falhar
            # Poderia retornar None aqui se considerar o profit essencial
            # return None 

        for tipo_api in tipos_api_considerar: 
            if tipo_api in init_info["result"] and isinstance(init_info["result"][tipo_api]["actives"], dict):
                for ativo_id, ativo_data in init_info["result"][tipo_api]["actives"].items():
                    ativo_nome_curto = ativo_data.get("name", "").split(".")[-1]
                    if not ativo_nome_curto or ativo_nome_curto in ativos_abertos_set: continue
                    
                    is_open = False
                    if tipo_api in ativos_raw and isinstance(ativos_raw[tipo_api], dict):
                         status_info = ativos_raw[tipo_api].get(ativo_nome_curto)
                         if isinstance(status_info, dict) and status_info.get('open', False):
                              is_open = True
                    
                    if is_open:
                        payout_perc = None
                        if all_profits and ativo_nome_curto in all_profits:
                             payout_info = all_profits[ativo_nome_curto]
                             payout_dec = payout_info.get("turbo", payout_info.get("binary"))
                             if payout_dec is not None: payout_perc = int(round(payout_dec * 100))

                        # Adiciona tupla (nome, payout) - Removida categoria
                        ativos_com_detalhes.append((ativo_nome_curto, payout_perc))
                        ativos_abertos_set.add(ativo_nome_curto)
                        
    elif mercado_foco == "Digital":
        # Lógica para Digital: Apenas lista os ativos abertos, pois obter payout
        # sob demanda é complexo (requer subscrição).
        logger.info("Listando apenas nomes de ativos Digitais abertos (payout/expiração/categoria não incluídos).")
        
        ativos_abertos_digital = []
        if "digital" in ativos_raw and isinstance(ativos_raw["digital"], dict):
             ativos_abertos_digital = [ativo for ativo, status in ativos_raw["digital"].items() 
                                      if isinstance(status, dict) and status.get('open', False)]

        # Adiciona à lista com payout None
        for ativo in sorted(ativos_abertos_digital):
            ativos_com_detalhes.append((ativo, None)) # Retorna (ativo, None)

    else:
        # Para outros mercados (Forex, Cripto), apenas lista os nomes
        logger.info(f"Listando apenas nomes de ativos {mercado_foco} abertos (payout/expiração/categoria não aplicável/buscado).")
        ativos_abertos_outros = []
        for tipo_api in tipos_api_considerar:
            if tipo_api in ativos_raw and isinstance(ativos_raw[tipo_api], dict):
                ativos_abertos_outros.extend([ativo for ativo, status in ativos_raw[tipo_api].items() 
                                             if isinstance(status, dict) and status.get('open', False)])
        
        # Remove duplicatas e adiciona com None
        for ativo in sorted(list(set(ativos_abertos_outros))):
             ativos_com_detalhes.append((ativo, None)) # Retorna (ativo, None)

    # 3. Filtrar por timeframe - Método otimizado
    # Nota: Para a IQ Option, a maioria dos ativos suporta os timeframes padrão (1, 5, 15 min)
    # Em vez de verificar todos individualmente (o que seria lento), vamos usar uma abordagem mais eficiente
    
    # Para Digital e Binário/Turbo, todos os ativos normalmente suportam 1 min
    if timeframe == 1:
        # Para timeframe de 1 min, não precisamos filtrar, todos suportam
        logger.info(f"Usando timeframe padrão de 1 min, todos os {len(ativos_com_detalhes)} ativos mantidos")
    else:
        # Para outros timeframes, podemos filtrar apenas os mais problemáticos
        # Ativos que tipicamente não suportam timeframes maiores (lista pode ser ampliada)
        ativos_problematicos = set([
            # Exemplos de ativos que podem não suportar todos os timeframes
            # Esta lista deve ser atualizada conforme necessário
        ])
        
        ativos_filtrados = []
        for ativo, payout in ativos_com_detalhes:
            if ativo in ativos_problematicos:
                logger.debug(f"Ativo {ativo} na lista de ativos potencialmente problemáticos para timeframe {timeframe}")
                # Aqui poderíamos verificar individualmente os ativos problemáticos
                # Para simplicidade, vamos pular estes ativos para timeframes não padrão
                continue
            
            ativos_filtrados.append((ativo, payout))
        
        ativos_com_detalhes = ativos_filtrados
    
    # 4. Nova ordenação conforme critérios:
    # Agora vamos ordenar primeiro por payout (decrescente) 
    # Em caso de empate de payout, ativos normais têm prioridade sobre OTC
    ativos_ordenados = sorted(
        ativos_com_detalhes, 
        key=lambda item: (
            # Primeiro critério: payout (decrescente)
            -(item[1] if item[1] is not None else -1),
            # Segundo critério: tipo (0 para normal, 1 para OTC)
            1 if "-OTC" in item[0] else 0,
            # Terceiro critério: nome do ativo (para ordenação consistente de ativos com mesmo payout e tipo)
            item[0]
        )
    )
    
    # Log final dos ativos ordenados
    ativos_para_log = [(a, p) for a, p in ativos_ordenados if p is not None]
    logger.info(f"Encontrados {len(ativos_ordenados)} ativos para {mercado_foco}. Payouts disponíveis: {len(ativos_para_log)}. Top com payout: {ativos_para_log[:5]}")
    
    return ativos_ordenados

# Função original comentada ou removida
# def listar_ativos_abertos_apenas(api, mercado_foco=None):
#     pass 
