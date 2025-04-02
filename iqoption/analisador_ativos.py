#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para análise de ativos na IQ Option
Inclui funções para categorizar ativos por volatilidade, tendência e identificar melhores oportunidades
"""

import os
import time
import logging
import random
import numpy as np
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Importações locais
from iqoption.ativos import listar_ativos_abertos_com_payout

# Configurar logger
logger = logging.getLogger(__name__)

# Constantes para análise
MAX_TENTATIVAS_RECONEXAO = 3
PAUSA_ENTRE_REQUISICOES = 0.5  # segundos entre requisições
PAUSA_APOS_ERRO = 2.0  # segundos após erro de conexão
MAX_ATIVOS_POR_BATCH = 20  # número máximo de ativos por lote
MAX_VELAS_POR_REQUISICAO = 1000  # Limite da API IQ Option

# Definições de categorias
CATEGORIAS_VOLATILIDADE = {
    0: "Baixa",
    1: "Média", 
    2: "Alta"
}

CATEGORIAS_TENDENCIA = {
    0: "Lateral",
    1: "Fraca",
    2: "Forte"
}

CATEGORIAS_LIQUIDEZ = {
    0: "Baixa",
    1: "Média",
    2: "Alta"
}

# Pesos para diferentes mercados
PESOS_MERCADOS = {
    "Binário/Turbo": {
        "volatilidade": 0.3,
        "tendencia": 0.4,
        "liquidez": 0.1,
        "payout": 0.2
    },
    "Digital": {
        "volatilidade": 0.25,
        "tendencia": 0.35,
        "liquidez": 0.1,
        "payout": 0.3
    },
    "Forex": {
        "volatilidade": 0.35,
        "tendencia": 0.25,
        "liquidez": 0.3,
        "payout": 0.1
    },
    "Cripto": {
        "volatilidade": 0.4,
        "tendencia": 0.3,
        "liquidez": 0.2,
        "payout": 0.1
    }
}

def obter_dados_historicos_seguro(api, ativo, timeframe, periodo, callback_progresso=None):
    """
    Obtém dados históricos de um ativo com tratamento de erros e reconexão
    Respeita o limite de 1000 velas por requisição da API
    
    Args:
        api: Instância da API IQ Option
        ativo: Nome do ativo
        timeframe: Timeframe em segundos (60, 300, etc)
        periodo: Número de velas para obter
        callback_progresso: Função para reportar progresso
        
    Returns:
        pd.DataFrame: Dataframe com os dados, ou None em caso de falha
    """
    logger.info(f"Obtendo {periodo} velas para {ativo} em timeframe {timeframe}s")
    
    # Verifica se o período está dentro do limite
    periodo_efetivo = min(periodo, MAX_VELAS_POR_REQUISICAO)
    
    # Obtém timestamp atual
    timestamp_atual = int(time.time())
    
    for tentativa in range(1, MAX_TENTATIVAS_RECONEXAO + 1):
        try:
            # Pausa entre requisições para evitar sobrecarga
            if tentativa > 1:
                # Pausa maior nas tentativas subsequentes
                time.sleep(PAUSA_ENTRE_REQUISICOES * tentativa)
            
            logger.info(f"Tentativa {tentativa}/{MAX_TENTATIVAS_RECONEXAO}: Obtendo {periodo_efetivo} velas para {ativo}")
            
            # Obtém velas - abordagem direta
            velas = api.get_candles(ativo, timeframe, periodo_efetivo, timestamp_atual)
            
            if velas and len(velas) > 0:
                logger.info(f"Sucesso! Obtidas {len(velas)} velas para {ativo}")
                
                # Converte para DataFrame
                df = pd.DataFrame(velas)
                
                # Adiciona coluna de data legível
                df['datetime'] = pd.to_datetime(df['from'], unit='s')
                
                # Renomeia colunas para nomes mais intuitivos
                df = df.rename(columns={'max': 'high', 'min': 'low'})
                
                # Ordena por timestamp (mais recente primeiro)
                df = df.sort_values('from', ascending=False).reset_index(drop=True)
                
                return df
            else:
                logger.warning(f"Tentativa {tentativa}/{MAX_TENTATIVAS_RECONEXAO}: Nenhuma vela retornada para {ativo}")
        
        except Exception as e:
            logger.error(f"Tentativa {tentativa}/{MAX_TENTATIVAS_RECONEXAO}: Erro ao obter candles para {ativo}: {str(e)}")
            
            # Tenta reconectar se for erro de conexão
            if "need reconnect" in str(e).lower() or "socket" in str(e).lower():
                logger.info("Tentando reconectar à API...")
                time.sleep(2)  # Espera antes de tentar reconectar
                try:
                    api.connect()
                    logger.info("Reconexão bem-sucedida")
                except Exception as reconnect_error:
                    logger.error(f"Falha na reconexão: {str(reconnect_error)}")
    
    # Se chegou aqui, todas as tentativas falharam
    logger.error(f"Falha ao obter velas para {ativo} após {MAX_TENTATIVAS_RECONEXAO} tentativas")
    return None

def calcular_metricas_ativo(df):
    """
    Calcula métricas importantes para análise do ativo
    
    Args:
        df: DataFrame pandas com dados históricos do ativo
        
    Returns:
        Dicionário com métricas calculadas ou None em caso de dados insuficientes
    """
    try:
        # Verifica se há dados suficientes
        if df is None or len(df) < 20:
            return None
            
        # Calcula volatilidade (desvio padrão normalizado dos retornos)
        df['retorno'] = df['close'].pct_change()
        volatilidade = df['retorno'].std() * np.sqrt(len(df))
        
        # Calcula range médio diário
        df['range'] = df['high'] - df['low']
        range_medio = df['range'].mean() / df['close'].mean()
        
        # Direção do preço (tendência simples)
        primeiro_preco = df['close'].iloc[0] if not df.empty else 0
        ultimo_preco = df['close'].iloc[-1] if not df.empty else 0
        variacao_percentual = ((ultimo_preco - primeiro_preco) / primeiro_preco) if primeiro_preco > 0 else 0
        
        # Calcula RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean().iloc[-1]
        avg_loss = loss.rolling(window=14).mean().iloc[-1]
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50  # Valor neutro se não houver perdas
        
        # Relação com as médias móveis
        ma_20 = df['close'].rolling(window=20).mean().iloc[-1]
        ma_50 = df['close'].rolling(window=50).mean().iloc[-1]
        relacao_mas = ultimo_preco / ma_20 if ma_20 > 0 else 1
        
        # Volume médio
        volume_medio = df['volume'].mean() if 'volume' in df.columns else 0
        
        return {
            'volatilidade': volatilidade,
            'range_medio': range_medio,
            'variacao_percentual': variacao_percentual,
            'rsi': rsi,
            'relacao_mas': relacao_mas,
            'volume_medio': volume_medio
        }
    except Exception as e:
        logger.error(f"Erro ao calcular métricas: {str(e)}")
        return None

def categorizar_ativos(api, ativos_abertos, mercado="Binário/Turbo", progress_callback=None):
    """
    Categoriza ativos em grupos de volatilidade, tendência e liquidez
    usando machine learning (K-means)
    
    Args:
        api: Objeto API IQ Option conectado
        ativos_abertos: Lista de ativos disponíveis com seus payouts
        mercado: String com o tipo de mercado (Binário/Turbo, Digital, etc)
        progress_callback: Função callback para atualizar progresso (opcional)
        
    Returns:
        DataFrame com ativos categorizados e pontuados
    """
    
    logger.info(f"Categorizando {len(ativos_abertos)} ativos...")
    
    # Inicializa dicionário para armazenar métricas de cada ativo
    metricas_ativos = {}
    
    # Obtém dados históricos para cada ativo
    logger.info(f"Obtendo dados históricos de {len(ativos_abertos)} ativos...")
    
    # Dividir ativos em lotes menores para processamento
    lotes_ativos = [ativos_abertos[i:i + MAX_ATIVOS_POR_BATCH] 
                    for i in range(0, len(ativos_abertos), MAX_ATIVOS_POR_BATCH)]
    
    contador_total = 0
    
    # Processa cada lote de ativos
    for indice_lote, lote in enumerate(lotes_ativos):
        logger.info(f"Processando lote {indice_lote + 1}/{len(lotes_ativos)} ({len(lote)} ativos)")
        
        # Adiciona uma pausa aleatória entre lotes para evitar padrões de requisição
        if indice_lote > 0:
            pausa_entre_lotes = random.uniform(1.0, 3.0)
            time.sleep(pausa_entre_lotes)
        
        # Cria barra de progresso para este lote
        pbar = tqdm(lote, desc=f"Lote {indice_lote + 1}", leave=False)
        
        for ativo_info in pbar:
            ativo, payout = ativo_info
            contador_total += 1
            
            # Atualiza descrição da barra de progresso
            pbar.set_description(f"Analisando {ativo}")
            
            # Pausa entre requisições para não sobrecarregar a API
            time.sleep(PAUSA_ENTRE_REQUISICOES)
            
            # Obtém dados históricos com tratamento de reconexão
            df = obter_dados_historicos_seguro(api, ativo, timeframe=60, quantidade=100, 
                                             max_tentativas=MAX_TENTATIVAS_RECONEXAO)
            
            # Calcula métricas
            metricas = calcular_metricas_ativo(df)
            
            if metricas:
                # Adiciona o payout
                metricas['payout'] = payout / 100.0  # Converte para decimal
                metricas_ativos[ativo] = metricas
                
            # Atualiza progresso geral
            if progress_callback:
                progress_callback(contador_total / len(ativos_abertos) * 100)
    
    # Verifica se há métricas suficientes
    if len(metricas_ativos) < 3:
        logger.error(f"Dados insuficientes para categorização. Obtidas métricas para apenas {len(metricas_ativos)} ativos.")
        return None
    
    # Cria DataFrame com todas as métricas
    logger.info(f"Criando DataFrame de métricas para {len(metricas_ativos)} ativos...")
    df_metricas = pd.DataFrame.from_dict(metricas_ativos, orient='index')
    
    # Normaliza os dados para clustering
    scaler = StandardScaler()
    
    # Colunas para classificação de volatilidade
    colunas_volatilidade = ['volatilidade', 'range_medio']
    if all(col in df_metricas.columns for col in colunas_volatilidade):
        df_vol = df_metricas[colunas_volatilidade].copy()
        df_vol_scaled = scaler.fit_transform(df_vol)
        
        # Aplica K-means para volatilidade (3 grupos)
        kmeans_vol = KMeans(n_clusters=3, random_state=42, n_init=10)
        df_metricas['cluster_volatilidade'] = kmeans_vol.fit_predict(df_vol_scaled)
        
        # Ordena os clusters pelo valor médio de volatilidade
        vol_order = df_metricas.groupby('cluster_volatilidade')['volatilidade'].mean().sort_values().index
        vol_mapping = {cluster: idx for idx, cluster in enumerate(vol_order)}
        df_metricas['volatilidade_categoria'] = df_metricas['cluster_volatilidade'].map(vol_mapping)
        df_metricas['volatilidade_nome'] = df_metricas['volatilidade_categoria'].map(CATEGORIAS_VOLATILIDADE)
    
    # Colunas para classificação de tendência
    colunas_tendencia = ['variacao_percentual', 'rsi', 'relacao_mas']
    if all(col in df_metricas.columns for col in colunas_tendencia):
        df_tend = df_metricas[colunas_tendencia].copy()
        df_tend_scaled = scaler.fit_transform(df_tend)
        
        # Aplica K-means para tendência (3 grupos)
        kmeans_tend = KMeans(n_clusters=3, random_state=42, n_init=10)
        df_metricas['cluster_tendencia'] = kmeans_tend.fit_predict(df_tend_scaled)
        
        # Ordena os clusters por variação percentual média
        tend_order = df_metricas.groupby('cluster_tendencia')['variacao_percentual'].mean().sort_values().index
        tend_mapping = {cluster: idx for idx, cluster in enumerate(tend_order)}
        df_metricas['tendencia_categoria'] = df_metricas['cluster_tendencia'].map(tend_mapping)
        df_metricas['tendencia_nome'] = df_metricas['tendencia_categoria'].map(CATEGORIAS_TENDENCIA)
    
    # Atribui categoria de liquidez com base no volume médio
    if 'volume_medio' in df_metricas.columns:
        vol_values = df_metricas['volume_medio'].values.reshape(-1, 1)
        vol_scaled = scaler.fit_transform(vol_values)
        
        # Aplica K-means para liquidez (3 grupos)
        kmeans_liq = KMeans(n_clusters=3, random_state=42, n_init=10)
        df_metricas['cluster_liquidez'] = kmeans_liq.fit_predict(vol_scaled)
        
        # Ordena os clusters por volume médio
        liq_order = df_metricas.groupby('cluster_liquidez')['volume_medio'].mean().sort_values().index
        liq_mapping = {cluster: idx for idx, cluster in enumerate(liq_order)}
        df_metricas['liquidez_categoria'] = df_metricas['cluster_liquidez'].map(liq_mapping)
        df_metricas['liquidez_nome'] = df_metricas['liquidez_categoria'].map(CATEGORIAS_LIQUIDEZ)
    
    # Calcula pontuação final ponderada
    pesos = PESOS_MERCADOS.get(mercado, PESOS_MERCADOS["Binário/Turbo"])
    
    df_metricas['pontuacao'] = (
        pesos['volatilidade'] * df_metricas['volatilidade_categoria'] +
        pesos['tendencia'] * df_metricas['tendencia_categoria'] +
        pesos['liquidez'] * df_metricas.get('liquidez_categoria', 1) +
        pesos['payout'] * df_metricas['payout'] * 3  # Multiplica por 3 para normalizar com categorias 0-2
    )
    
    # Ordena pelo score final
    df_metricas = df_metricas.sort_values('pontuacao', ascending=False)
    
    logger.info(f"Análise concluída. Ativos categorizados: {len(df_metricas)}")
    
    return df_metricas

def salvar_resultados_html(df_metricas, mercado, payout_minimo=0):
    """
    Salva resultados da análise em um arquivo HTML formatado
    
    Args:
        df_metricas: DataFrame pandas com métricas e categorias
        mercado: String com o tipo de mercado
        payout_minimo: Payout mínimo usado no filtro (%)
    
    Returns:
        Caminho para o arquivo HTML gerado
    """
    if df_metricas is None or df_metricas.empty:
        logger.error("Sem dados para gerar relatório HTML")
        return None
    
    # Cria diretório para relatórios se não existir
    reports_dir = "relatorios"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Data formatada para o nome do arquivo
    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    mercado_fmt = mercado.replace("/", "_").replace(" ", "_").lower()
    
    # Nome do arquivo (inclui informação de payout mínimo se aplicável)
    if payout_minimo > 0:
        filename = os.path.join(reports_dir, f"analise_{mercado_fmt}_payout{payout_minimo}_{data_hora}.html")
    else:
        filename = os.path.join(reports_dir, f"analise_{mercado_fmt}_{data_hora}.html")
    
    # Formatação HTML
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Análise de Ativos - {mercado}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #2c3e50; }}
            .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #ddd; }}
            .volatility-low {{ background-color: #d4edda; }}
            .volatility-medium {{ background-color: #fff3cd; }}
            .volatility-high {{ background-color: #f8d7da; }}
            .trend-lateral {{ background-color: #e2e3e5; }}
            .trend-weak {{ background-color: #cce5ff; }}
            .trend-strong {{ background-color: #d1ecf1; }}
            .top-10 {{ font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Análise de Ativos - Mercado {mercado}</h1>
        <div class="summary">
            <h2>Resumo da Análise</h2>
            <p>Data da análise: {data_analise}</p>
            <p>Total de ativos analisados: {total_ativos}</p>
            <p>Payout mínimo: {payout_minimo}%</p>
            <p>Melhor ativo: {melhor_ativo} (Pontuação: {melhor_pontuacao:.2f})</p>
        </div>
        
        <h2>Top 10 Ativos Recomendados</h2>
        {tabela_top10}
        
        <h2>Todos os Ativos Analisados</h2>
        {tabela_completa}
    </body>
    </html>
    """
    
    # Formatar top 10
    df_top10 = df_metricas.head(10).copy()
    
    # Formatar tabela top 10
    tabela_top10 = df_top10.to_html(classes='dataframe',
                                    columns=['payout', 'volatilidade_nome', 'tendencia_nome', 
                                             'liquidez_nome', 'pontuacao'],
                                    float_format=lambda x: f"{x:.2f}")
    
    # Formatar tabela completa
    tabela_completa = df_metricas.to_html(classes='dataframe',
                                         columns=['payout', 'volatilidade_nome', 'tendencia_nome', 
                                                  'liquidez_nome', 'pontuacao'],
                                         float_format=lambda x: f"{x:.2f}")
    
    # Preencher o template
    html_content = html_template.format(
        mercado=mercado,
        data_analise=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        total_ativos=len(df_metricas),
        payout_minimo=payout_minimo,
        melhor_ativo=df_metricas.index[0] if not df_metricas.empty else "N/A",
        melhor_pontuacao=df_metricas['pontuacao'].iloc[0] if not df_metricas.empty else 0,
        tabela_top10=tabela_top10,
        tabela_completa=tabela_completa
    )
    
    # Salvar arquivo
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Relatório salvo em {filename}")
    return filename

def interface_analise_ativos(api, tipo_mercado="Binário/Turbo", callback_progresso=None, payout_minimo=85):
    """Interface para análise de ativos com tratamento de erros e gerenciamento de progresso"""
    logger.info(f"Iniciando análise completa para o mercado: {tipo_mercado} (Payout mínimo: {payout_minimo}%)")
    
    try:
        # Iniciar análise 
        analise = AnalisadorAtivos(api)
        
        # Buscar ativos com payouts
        ativos_info = analise.buscar_ativos_payouts(tipo_mercado, payout_minimo)
        if not ativos_info:
            logger.error(f"Nenhum ativo encontrado para {tipo_mercado} com payout mínimo de {payout_minimo}%")
            return None, None
        
        # Analisar e categorizar ativos
        df_metricas, caminho_html = analise.executar_analise_completa(
            ativos_info, 
            tipo_mercado,
            timeframes_analise=[60],  # Foco apenas no timeframe de 1 minuto que parece mais confiável
            periodo_analise=1000,      # Máximo de 1000 velas por requisição
            callback_progresso=callback_progresso,
            payout_minimo=payout_minimo
        )
        
        return df_metricas, caminho_html
        
    except KeyboardInterrupt:
        logger.warning("Análise de ativos interrompida pelo usuário")
        return None, None
        
    except Exception as e:
        logger.exception(f"Erro durante análise de ativos: {str(e)}")
        return None, None

def processar_velas_para_dataframe(velas):
    """
    Converte lista de velas em DataFrame pandas
    
    Args:
        velas: Lista de dicionários com dados de velas
        
    Returns:
        pd.DataFrame: DataFrame formatado com os dados das velas
    """
    if not velas:
        return None
        
    # Converte para DataFrame
    df = pd.DataFrame(velas)
    
    # Adiciona coluna de data legível para análise
    df['datetime'] = pd.to_datetime(df['from'], unit='s')
    
    # Renomeia colunas para nomes mais intuitivos
    df = df.rename(columns={'max': 'high', 'min': 'low'})
    
    # Ordena por data/hora (mais recente primeiro)
    df = df.sort_values('from', ascending=False).reset_index(drop=True)
    
    return df 

class AnalisadorAtivos:
    """
    Classe para análise de ativos da IQ Option
    Implementa mecanismos de reconexão e limites para evitar problemas de conexão
    """
    
    def __init__(self, api):
        """
        Inicializa o analisador de ativos
        
        Args:
            api: Instância da API IQ Option conectada
        """
        self.api = api
        self.logger = logging.getLogger(__name__)
    
    def buscar_ativos_payouts(self, tipo_mercado, payout_minimo=0):
        """
        Busca ativos disponíveis com seus payouts, filtrando por payout mínimo
        
        Args:
            tipo_mercado: Tipo de mercado (ex: Binário/Turbo, Digital)
            payout_minimo: Payout mínimo para incluir o ativo (em %)
            
        Returns:
            dict: Dicionário com ativos e payouts ou None em caso de erro
        """
        from iqoption.ativos import listar_ativos_abertos_com_payout
        ativos_lista = listar_ativos_abertos_com_payout(self.api, tipo_mercado)
        
        # Converte a lista de tuplas para dicionário e aplica filtro de payout
        if isinstance(ativos_lista, list):
            ativos_dict = {}
            ativos_filtrados = 0
            
            for ativo, payout in ativos_lista:
                if payout >= payout_minimo:
                    ativos_dict[ativo] = payout
                else:
                    ativos_filtrados += 1
            
            if ativos_filtrados > 0:
                self.logger.info(f"Filtrados {ativos_filtrados} ativos com payout abaixo de {payout_minimo}%")
                
            return ativos_dict
        
        return ativos_lista
    
    def analisar_ativo(self, ativo, timeframe, periodo):
        """
        Analisa um ativo individual, calculando métricas
        
        Args:
            ativo: Nome do ativo
            timeframe: Timeframe em segundos
            periodo: Número de velas para análise
            
        Returns:
            dict: Dicionário com métricas ou None em caso de erro
        """
        # Obter dados históricos
        df = obter_dados_historicos_seguro(self.api, ativo, timeframe, periodo)
        
        if df is None:
            self.logger.warning(f"Não foi possível obter dados para {ativo}")
            return None
        
        if df.empty or len(df) < 20:  # Precisamos de pelo menos 20 velas para análise
            self.logger.warning(f"Dados insuficientes para {ativo}. Velas obtidas: {len(df) if df is not None else 0}")
            return None
        
        self.logger.info(f"Analisando {len(df)} velas para {ativo} em timeframe {timeframe}s")
        
        try:
            # Calcular métricas básicas
            metricas = {}
            
            # Preços de referência
            ultimo_preco = df['close'].iloc[0]
            primeiro_preco = df['close'].iloc[-1]
            
            # Amplitude de preços
            max_preco = df['high'].max()
            min_preco = df['low'].min()
            amplitude = (max_preco - min_preco) / min_preco * 100 if min_preco > 0 else 0
            
            # Tendência (usando média móvel)
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            
            # Determina tendência atual
            if not df['ma20'].iloc[0:20].isna().all() and not df['ma50'].iloc[0:50].isna().all():
                ultimo_ma20 = df['ma20'].iloc[0]
                ultimo_ma50 = df['ma50'].iloc[0]
                
                diferenca_percentual = ((ultimo_ma20 / ultimo_ma50) - 1) * 100
                
                # Categoriza tendência baseada na diferença percentual
                if diferenca_percentual > 1.0:
                    tendencia = 2  # Alta forte
                elif diferenca_percentual > 0.2:
                    tendencia = 1  # Alta
                elif diferenca_percentual < -1.0:
                    tendencia = -2  # Baixa forte
                elif diferenca_percentual < -0.2:
                    tendencia = -1  # Baixa
                else:
                    tendencia = 0  # Neutra
                    
                self.logger.debug(f"{ativo}: Diferença MA20/MA50: {diferenca_percentual:.2f}% -> Tendência: {tendencia}")
            else:
                tendencia = 0
                self.logger.debug(f"{ativo}: Dados insuficientes para calcular MAs completas")
            
            # Volatilidade (usando desvio padrão normalizado)
            retornos = df['close'].pct_change().dropna()
            if len(retornos) > 0:
                volatilidade = retornos.std() * 100
                
                # Classifica volatilidade
                if volatilidade > 2.5:
                    vol_cat = 3  # Muito alta
                elif volatilidade > 1.5:
                    vol_cat = 2  # Alta
                elif volatilidade > 0.8:
                    vol_cat = 1  # Média
                else:
                    vol_cat = 0  # Baixa
                    
                self.logger.debug(f"{ativo}: Volatilidade: {volatilidade:.2f}% -> Categoria: {vol_cat}")
            else:
                volatilidade = 0
                vol_cat = 0
                self.logger.debug(f"{ativo}: Dados insuficientes para calcular volatilidade")
            
            # Calcular RSI
            delta = df['close'].diff().dropna()
            if len(delta) > 0:
                ganhos = delta.where(delta > 0, 0)
                perdas = -delta.where(delta < 0, 0)
                
                window = min(14, len(ganhos))
                avg_ganho = ganhos.rolling(window=window).mean().dropna()
                avg_perda = perdas.rolling(window=window).mean().dropna()
                
                if not avg_perda.empty and not avg_ganho.empty and avg_perda.iloc[-1] != 0:
                    rs = avg_ganho.iloc[-1] / avg_perda.iloc[-1]
                    rsi = 100 - (100 / (1 + rs))
                else:
                    rsi = 50
                
                self.logger.debug(f"{ativo}: RSI: {rsi:.2f}")
            else:
                rsi = 50
            
            # Adiciona todas as métricas
            metricas['tendencia'] = tendencia
            metricas['amplitude'] = amplitude
            metricas['volatilidade'] = volatilidade
            metricas['volatilidade_categoria'] = vol_cat
            metricas['rsi'] = rsi
            
            # Indicadores adicionais para decisão
            metricas['preco_vs_ma20'] = (ultimo_preco / ultimo_ma20 - 1) * 100 if not np.isnan(ultimo_ma20) and ultimo_ma20 > 0 else 0
            metricas['preco_vs_ma50'] = (ultimo_preco / ultimo_ma50 - 1) * 100 if not np.isnan(ultimo_ma50) and ultimo_ma50 > 0 else 0
            
            self.logger.info(f"Métricas calculadas com sucesso para {ativo} em timeframe {timeframe}s")
            return metricas
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar {ativo}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def executar_analise_completa(self, ativos_info, tipo_mercado, timeframes_analise=[60], 
                                periodo_analise=1000, callback_progresso=None, payout_minimo=0):
        """
        Executa análise completa de todos os ativos
        
        Args:
            ativos_info: Dicionário com informações de ativos e payouts
            tipo_mercado: Tipo de mercado (ex: Binário/Turbo)
            timeframes_analise: Lista de timeframes para análise (em segundos)
            periodo_analise: Quantidade de velas para análise
            callback_progresso: Função para reportar progresso
            payout_minimo: Payout mínimo para considerar ativos (%)
            
        Returns:
            tuple: (DataFrame com métricas, caminho relatório HTML)
        """
        total_ativos = len(ativos_info)
        self.logger.info(f"Categorizando {total_ativos} ativos (Payout ≥ {payout_minimo}%)...")
        
        if callback_progresso:
            callback_progresso(10, f"Analisando {total_ativos} ativos (Payout ≥ {payout_minimo}%)...")
        
        # Inicializa dicionário para armazenar resultados
        resultados = {}
        
        # Lista de ativos
        ativos_lista = list(ativos_info.keys())
        
        # Divide em lotes para evitar sobrecarga
        num_lotes = (len(ativos_lista) + MAX_ATIVOS_POR_BATCH - 1) // MAX_ATIVOS_POR_BATCH
        self.logger.info(f"Processando {len(ativos_lista)} ativos em {num_lotes} lotes")
        
        # Contador de sucessos e falhas
        ativos_analisados = 0
        ativos_com_erro = 0
        
        # Para cada lote de ativos
        for i_lote in range(num_lotes):
            inicio = i_lote * MAX_ATIVOS_POR_BATCH
            fim = min(inicio + MAX_ATIVOS_POR_BATCH, len(ativos_lista))
            lote_atual = ativos_lista[inicio:fim]
            
            self.logger.info(f"Processando lote {i_lote+1}/{num_lotes}: {len(lote_atual)} ativos")
            
            # Para cada ativo no lote
            for idx, ativo in enumerate(lote_atual):
                try:
                    # Calcula progresso atual
                    progresso_atual = ((i_lote * MAX_ATIVOS_POR_BATCH + idx) / len(ativos_lista)) * 100
                    
                    # Callback de progresso
                    if callback_progresso:
                        # Mapeia para faixa de 10-90%
                        progresso_ajustado = 10 + (progresso_atual * 0.8)
                        callback_progresso(progresso_ajustado, f"Analisando {ativo}...")
                    
                    # Payout
                    payout = ativos_info[ativo] / 100.0
                    
                    # Inicializa métricas
                    metricas_ativo = {
                        'payout': payout,
                    }
                    
                    # Usamos apenas o primeiro timeframe da lista (tipicamente 60s)
                    if len(timeframes_analise) > 0:
                        timeframe = timeframes_analise[0]
                        
                        # Pequena pausa antes da requisição
                        time.sleep(PAUSA_ENTRE_REQUISICOES / 2)
                        
                        # Tenta obter métricas
                        metricas_tf = self.analisar_ativo(ativo, timeframe, periodo_analise)
                        
                        if metricas_tf:
                            # Atualiza contadores
                            ativos_analisados += 1
                            
                            # Copia métricas para o resultado
                            for chave, valor in metricas_tf.items():
                                metricas_ativo[chave] = valor
                            
                            # Adiciona nomes textuais para categorias
                            tendencia_cat = 0
                            if 'tendencia' in metricas_tf:
                                tendencia = metricas_tf['tendencia']
                                if tendencia > 1.5:
                                    tendencia_cat = 2  # Alta forte
                                elif tendencia > 0.5:
                                    tendencia_cat = 1  # Alta
                                elif tendencia < -1.5:
                                    tendencia_cat = -2  # Baixa forte
                                elif tendencia < -0.5:
                                    tendencia_cat = -1  # Baixa
                                else:
                                    tendencia_cat = 0  # Neutra/Lateral
                            
                            vol_cat = 0
                            if 'volatilidade_categoria' in metricas_tf:
                                vol_cat = metricas_tf['volatilidade_categoria']
                                
                            # Adiciona nomes às categorias
                            metricas_ativo['tendencia_categoria'] = tendencia_cat
                            metricas_ativo['tendencia_nome'] = CATEGORIAS_TENDENCIA.get(tendencia_cat, "Lateral")
                            metricas_ativo['volatilidade_nome'] = CATEGORIAS_VOLATILIDADE.get(vol_cat, "Baixa")
                            
                            # Calcula pontuação
                            tendencia_abs = abs(tendencia_cat)
                            payout_norm = (payout - 0.7) / 0.3 if payout > 0.7 else 0  # Normaliza entre 0.7 e 1.0
                            
                            pontuacao = (vol_cat * 1.5) + (tendencia_abs * 1) + (payout_norm * 5)
                            metricas_ativo['pontuacao'] = pontuacao
                            
                            # Adiciona aos resultados
                            resultados[ativo] = metricas_ativo
                        else:
                            ativos_com_erro += 1
                            self.logger.warning(f"Não foi possível analisar o ativo {ativo}")
                
                except Exception as e:
                    ativos_com_erro += 1
                    self.logger.error(f"Erro ao processar ativo {ativo}: {str(e)}")
                
                # Pequena pausa entre ativos do mesmo lote
                time.sleep(PAUSA_ENTRE_REQUISICOES)
            
            # Pausa maior entre lotes
            time.sleep(PAUSA_ENTRE_REQUISICOES * 2)
            
            # Log de progresso após cada lote
            self.logger.info(f"Progresso: {progresso_atual:.1f}% - Analisados: {ativos_analisados}, Falhas: {ativos_com_erro}")
        
        # Cria DataFrame a partir dos resultados
        if resultados:
            total_analisados = len(resultados)
            self.logger.info(f"Análise concluída. {total_analisados} ativos analisados com sucesso ({ativos_com_erro} falhas)")
            
            df_final = pd.DataFrame.from_dict(resultados, orient='index')
            
            # Ordena por pontuação (decrescente)
            df_final = df_final.sort_values('pontuacao', ascending=False)
            
            # Gera relatório HTML
            if callback_progresso:
                callback_progresso(90, f"Gerando relatório HTML (Payout ≥ {payout_minimo}%)...")
                
            caminho_html = salvar_resultados_html(df_final, tipo_mercado, payout_minimo)
            
            # Finaliza
            if callback_progresso:
                callback_progresso(100, "Análise concluída com sucesso!")
                
            return df_final, caminho_html
            
        else:
            self.logger.error("Nenhum ativo foi analisado com sucesso")
            return None, None 