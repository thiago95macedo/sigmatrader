"""
Módulo de preprocessamento de dados para modelos LSTM
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from collections import deque
import time
import logging

logger = logging.getLogger(__name__)

# Constantes
SEQ_LEN = 5  # Tamanho da sequência de entrada
FUTURE_PERIOD_PREDICT = 2  # Períodos futuros para previsão

def carregar_configuracao():
    """Carrega as configurações do arquivo config.ini ou usa os valores padrão"""
    import os
    import configparser
    
    config_dir = "configuracoes"
    config_path = os.path.join(config_dir, "lstm_config.ini")
    
    config_padrao = {
        'seq_len': SEQ_LEN,
        'future_predict': FUTURE_PERIOD_PREDICT
    }
    
    if os.path.exists(config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        
        if 'LSTM' in config:
            return {
                'seq_len': config['LSTM'].getint('seq_len', config_padrao['seq_len']),
                'future_predict': config['LSTM'].getint('future_predict', config_padrao['future_predict'])
            }
    
    return config_padrao

def classificar(atual, futuro):
    """Classifica a direção do movimento de preço"""
    return 1 if float(futuro) > float(atual) else 0

def obter_candles_historicos(api_iq, ativo, quantidade=1000, timeframe=1):
    """
    Obtém velas históricas do ativo
    
    Args:
        api_iq: API da IQ Option conectada
        ativo: Nome do ativo para obter velas
        quantidade: Quantidade de velas a serem obtidas
        timeframe: Timeframe em minutos (1, 5, 15, 30, 60, 240). Default: 1
        
    Returns:
        Lista de velas ou None em caso de erro
    """
    # Mapeamento de timeframe em minutos para segundos
    timeframes = {
        1: 60,     # 1 minuto
        5: 300,    # 5 minutos
        15: 900,   # 15 minutos
        30: 1800,  # 30 minutos
        60: 3600,  # 1 hora
        240: 14400 # 4 horas
    }
    
    # Verifica se o timeframe é válido
    if timeframe not in timeframes:
        logger.warning(f"Timeframe {timeframe} inválido. Usando timeframe padrão de 1 minuto.")
        timeframe = 1
    
    timeframe_segundos = timeframes[timeframe]
    logger.info(f"Obtendo {quantidade} velas históricas para {ativo} (Timeframe: {timeframe} min)")
    
    end_from_time = time.time()
    try:
        candles = api_iq.get_candles(ativo, timeframe_segundos, quantidade, end_from_time)
        
        if not candles:
            logger.error(f"Falha ao obter velas para {ativo}")
            return None
        
        logger.info(f"Obtidas {len(candles)} velas para {ativo}")
        return candles
    except Exception as e:
        logger.error(f"Erro ao obter velas: {e}")
        return None

def criar_dataframe_com_indicadores(candles):
    """Cria um DataFrame a partir das velas e adiciona indicadores técnicos"""
    logger.info("Processando dados e calculando indicadores técnicos")
    
    df = pd.DataFrame()
    
    # Converte os candles para DataFrame
    for candle in candles:
        novo = pd.DataFrame([candle])
        df = pd.concat([df, novo], ignore_index=True)
    
    # Renomeia as colunas para facilitar o acesso
    df.rename(columns={
        'open': 'abertura',
        'close': 'fechamento',
        'min': 'minimo',
        'max': 'maximo',
        'volume': 'volume'
    }, inplace=True)
    
    # Configura parâmetros do modelo
    config = carregar_configuracao()
    future_period = config['future_predict']
    
    # Cria o alvo para classificação
    df['futuro'] = df['fechamento'].shift(-future_period)
    
    # Adiciona indicadores técnicos
    # Médias Móveis
    df['MM20'] = df['fechamento'].rolling(window=20).mean()
    df['MM50'] = df['fechamento'].rolling(window=50).mean()
    
    # Médias Móveis Exponenciais
    df['EMA20'] = df['fechamento'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['fechamento'].ewm(span=50, adjust=False).mean()
    
    # Estocástico
    df['L14'] = df['minimo'].rolling(window=14).min()
    df['H14'] = df['maximo'].rolling(window=14).max()
    df['%K'] = 100 * ((df['fechamento'] - df['L14']) / (df['H14'] - df['L14']))
    df['%D'] = df['%K'].rolling(window=3).mean()
    
    # RSI
    rsi_periodo = 14
    delta = df['fechamento'].diff()
    ganho = delta.clip(lower=0)
    perda = -1 * delta.clip(upper=0)
    
    media_ganho = ganho.rolling(window=rsi_periodo).mean()
    media_perda = perda.rolling(window=rsi_periodo).mean()
    
    rs = media_ganho / media_perda
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Calcula o alvo (target)
    df['alvo'] = list(map(classificar, df['fechamento'], df['futuro']))
    
    # Remove colunas que não serão usadas para treinar o modelo
    colunas_para_remover = ['open', 'from', 'to', 'id', 'futuro', 'L14', 'H14']
    colunas_existentes = [col for col in colunas_para_remover if col in df.columns]
    df.drop(columns=colunas_existentes, inplace=True)
    
    # Remove linhas com NaN (devido ao cálculo dos indicadores)
    df.dropna(inplace=True)
    
    return df

def normalizar_dados(df, salvar_scaler=False):
    """Normaliza os dados entre 0 e 1"""
    logger.info("Normalizando dados")
    
    # A última coluna é o alvo (não será normalizado)
    alvo = df['alvo'].values
    dados = df.drop(columns=['alvo'])
    
    # Aplica normalização
    scaler = MinMaxScaler()
    dados_normalizados = scaler.fit_transform(dados)
    
    # Cria novo DataFrame com dados normalizados
    df_normalizado = pd.DataFrame(dados_normalizados, columns=dados.columns)
    df_normalizado['alvo'] = alvo
    
    if salvar_scaler:
        import joblib
        import os
        
        diretorio = "modelos"
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
        
        joblib.dump(scaler, os.path.join(diretorio, "scaler.pkl"))
        logger.info("Scaler salvo em modelos/scaler.pkl")
    
    return df_normalizado

def criar_sequencias(df):
    """
    Cria sequências temporais para treinar o modelo LSTM
    Retorna X (sequencias) e y (alvos)
    """
    logger.info("Criando sequências temporais para LSTM")
    
    # Configura o tamanho da sequência
    config = carregar_configuracao()
    seq_len = config['seq_len']
    
    # Prepara os dados sequenciais
    target_column = df.columns.get_loc('alvo')
    sequencias = []
    
    # Cria as sequências
    for i in range(len(df) - seq_len):
        # Sequência de entradas
        seq = df.iloc[i:i+seq_len].drop(columns=['alvo']).values
        # Alvo (última posição da sequência)
        target = df.iloc[i + seq_len - 1, target_column]
        sequencias.append((seq, target))
    
    # Balanceia os dados (mesmo número de CALL e PUT)
    call_sequencias = [s for s in sequencias if s[1] == 1]  # CALL (1)
    put_sequencias = [s for s in sequencias if s[1] == 0]   # PUT (0)
    
    # Equilibra as classes
    min_length = min(len(call_sequencias), len(put_sequencias))
    call_sequencias = call_sequencias[:min_length]
    put_sequencias = put_sequencias[:min_length]
    
    # Combina e embaralha
    sequencias_balanceadas = call_sequencias + put_sequencias
    np.random.shuffle(sequencias_balanceadas)
    
    # Separa X e y
    X = np.array([s[0] for s in sequencias_balanceadas])
    y = np.array([s[1] for s in sequencias_balanceadas])
    
    return X, y

def dividir_dados_treino_teste(X, y, split=0.2):
    """Divide os dados em conjuntos de treino e teste"""
    logger.info(f"Dividindo dados em treino ({100-split*100}%) e teste ({split*100}%)")
    
    # Calcula o ponto de divisão
    split_idx = int(len(X) * (1 - split))
    
    # Divide os dados
    X_treino, X_teste = X[:split_idx], X[split_idx:]
    y_treino, y_teste = y[:split_idx], y[split_idx:]
    
    return X_treino, X_teste, y_treino, y_teste

def preparar_dados_predicao(api_iq, ativo):
    """
    Prepara dados para fazer uma predição em tempo real
    Retorna um array formatado para entrada no modelo LSTM
    """
    logger.info(f"Preparando dados para predição em tempo real de {ativo}")
    
    # Obtém as velas mais recentes
    candles = obter_candles_historicos(api_iq, ativo, 100)  # Apenas 100 velas são suficientes
    if not candles:
        return None
    
    # Cria DataFrame com indicadores
    df = criar_dataframe_com_indicadores(candles)
    
    # Carrega o scaler salvo anteriormente
    import joblib
    import os
    
    scaler_path = os.path.join("modelos", "scaler.pkl")
    if not os.path.exists(scaler_path):
        logger.warning("Scaler não encontrado, usando normalização padrão")
        df_norm = normalizar_dados(df)
    else:
        # Normaliza usando o scaler salvo (para manter consistência)
        logger.info("Usando scaler pré-treinado para normalização")
        scaler = joblib.load(scaler_path)
        
        # Remove a coluna alvo para normalização
        alvo = df['alvo'].values
        dados = df.drop(columns=['alvo'])
        
        # Aplica o scaler
        dados_normalizados = scaler.transform(dados)
        
        # Recria o DataFrame normalizado
        df_norm = pd.DataFrame(dados_normalizados, columns=dados.columns)
        df_norm['alvo'] = alvo
    
    # Configura o tamanho da sequência
    config = carregar_configuracao()
    seq_len = config['seq_len']
    
    # Pega a sequência mais recente para predição
    ultima_sequencia = df_norm.iloc[-seq_len:].drop(columns=['alvo']).values
    
    # Formata a entrada para o modelo LSTM [1, seq_len, features]
    X_pred = np.expand_dims(ultima_sequencia, axis=0)
    
    return X_pred 