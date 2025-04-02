"""
Módulo para treinamento de modelos LSTM para previsão de mercado
"""

import os
import time
import logging
import tensorflow as tf
import numpy as np
from .preprocessamento import (
    obter_candles_historicos,
    criar_dataframe_com_indicadores,
    normalizar_dados,
    criar_sequencias,
    dividir_dados_treino_teste,
    carregar_configuracao
)

logger = logging.getLogger(__name__)

def criar_modelo_lstm(input_shape, learning_rate=0.001):
    """Cria o modelo LSTM para treinar"""
    logger.info(f"Criando modelo LSTM com input shape {input_shape}")
    
    model = tf.keras.models.Sequential([
        tf.keras.layers.LSTM(128, input_shape=input_shape, return_sequences=True),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.BatchNormalization(),
        
        tf.keras.layers.LSTM(128, return_sequences=True),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.BatchNormalization(),
        
        tf.keras.layers.LSTM(128),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.BatchNormalization(),
        
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        
        tf.keras.layers.Dense(2, activation='softmax')
    ])
    
    # Compilar o modelo
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(
        loss='sparse_categorical_crossentropy',
        optimizer=optimizer,
        metrics=['accuracy']
    )
    
    return model

def treinar_modelo(api_iq, ativo, timeframe=1, nome_modelo=None):
    """
    Treina um modelo LSTM para o ativo especificado
    
    Args:
        api_iq: API da IQ Option conectada
        ativo: Nome do ativo para treinar
        timeframe: Timeframe em minutos (1, 5, 15, 30, 60, 240). Default: 1
        nome_modelo: Nome personalizado para o modelo (opcional)
        
    Returns:
        Caminho para o modelo salvo
    """
    logger.info(f"Iniciando treinamento de modelo LSTM para {ativo} (Timeframe: {timeframe} min)")
    
    # Carrega configurações
    config = carregar_configuracao()
    seq_len = config['seq_len']
    
    # Cria diretório para modelos se não existir
    modelo_dir = "modelos"
    if not os.path.exists(modelo_dir):
        os.makedirs(modelo_dir)
    
    # Define nome do modelo
    if not nome_modelo:
        timestamp = int(time.time())
        nome_modelo = f"LSTM_{ativo}_TF{timeframe}_{timestamp}.keras"
    
    caminho_modelo = os.path.join(modelo_dir, nome_modelo)
    
    try:
        # 1. Obter dados históricos
        candles = obter_candles_historicos(api_iq, ativo, quantidade=1000, timeframe=timeframe)
        if not candles:
            logger.error(f"Não foi possível obter dados históricos para {ativo}")
            return None
            
        logger.info(f"Obtidas {len(candles)} velas históricas")
        
        # 2. Criar DataFrame com indicadores
        df = criar_dataframe_com_indicadores(candles)
        if df.empty:
            logger.error("DataFrame vazio após processamento")
            return None
        
        logger.info(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
        
        # 3. Normalizar dados
        df_normalizado = normalizar_dados(df, salvar_scaler=True)
        
        # 4. Criar sequências para LSTM
        X, y = criar_sequencias(df_normalizado)
        logger.info(f"Sequências criadas: X shape {X.shape}, y shape {y.shape}")
        
        # 5. Dividir dados em treino e teste
        X_treino, X_teste, y_treino, y_teste = dividir_dados_treino_teste(X, y, split=0.2)
        
        # 6. Criar o modelo
        input_shape = (X_treino.shape[1], X_treino.shape[2])
        model = criar_modelo_lstm(input_shape)
        
        # Callbacks para melhorar o treinamento
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        checkpoint = tf.keras.callbacks.ModelCheckpoint(
            caminho_modelo,
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        )
        
        # Carrega as configurações de batch size e epochs
        config = carregar_configuracao()
        batch_size = 16  # Valor padrão
        epochs = 40      # Valor padrão
        
        # Se disponíveis, usa as configurações do arquivo
        if os.path.exists("configuracoes/lstm_config.ini"):
            import configparser
            parser = configparser.ConfigParser()
            parser.read("configuracoes/lstm_config.ini")
            
            if 'LSTM' in parser:
                batch_size = parser['LSTM'].getint('batch_size', batch_size)
                epochs = parser['LSTM'].getint('epochs', epochs)
                
        # 7. Treinar o modelo
        logger.info(f"Iniciando treinamento com batch_size={batch_size}, epochs={epochs}")
        
        history = model.fit(
            X_treino, y_treino,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_teste, y_teste),
            callbacks=[early_stopping, checkpoint],
            verbose=1
        )
        
        # 8. Avaliar o modelo
        resultados = model.evaluate(X_teste, y_teste, verbose=1)
        logger.info(f"Avaliação do modelo - Perda: {resultados[0]:.4f}, Acurácia: {resultados[1]:.4f}")
        
        # 9. Salvar o modelo
        model.save(caminho_modelo)
        logger.info(f"Modelo salvo em {caminho_modelo}")
        
        return caminho_modelo
        
    except Exception as e:
        logger.error(f"Erro durante o treinamento: {e}", exc_info=True)
        return None

def atualizar_modelo(modelo_path, api_iq, ativo, timeframe=1):
    """
    Atualiza um modelo existente com novos dados
    
    Args:
        modelo_path: Caminho para o modelo existente
        api_iq: API da IQ Option conectada
        ativo: Nome do ativo para treinar
        timeframe: Timeframe em minutos (1, 5, 15, 30, 60, 240). Default: 1
        
    Returns:
        Caminho para o modelo atualizado
    """
    logger.info(f"Atualizando modelo {modelo_path} com novos dados de {ativo} (Timeframe: {timeframe} min)")
    
    try:
        # 1. Carregar o modelo existente
        if not os.path.exists(modelo_path):
            logger.error(f"Modelo não encontrado: {modelo_path}")
            return None
        
        model = tf.keras.models.load_model(modelo_path)
        
        # 2. Obter dados recentes
        candles = obter_candles_historicos(api_iq, ativo, quantidade=300, timeframe=timeframe)  # Menos dados para atualização
        if not candles:
            logger.error(f"Não foi possível obter dados recentes para {ativo}")
            return None
        
        # 3. Processar os novos dados
        df = criar_dataframe_com_indicadores(candles)
        df_normalizado = normalizar_dados(df)  # Não salva o scaler para atualização
        
        # 4. Criar sequências
        X, y = criar_sequencias(df_normalizado)
        
        # 5. Configurações para fine-tuning
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='loss',
            patience=3,
            restore_best_weights=True
        )
        
        # 6. Fine-tuning com menos épocas
        history = model.fit(
            X, y,
            epochs=20,
            batch_size=16,
            callbacks=[early_stopping],
            verbose=1
        )
        
        # 7. Salvar modelo atualizado
        timestamp = int(time.time())
        nome_atualizado = f"LSTM_{ativo}_TF{timeframe}_atualizado_{timestamp}.keras"
        caminho_atualizado = os.path.join("modelos", nome_atualizado)
        
        model.save(caminho_atualizado)
        logger.info(f"Modelo atualizado salvo em {caminho_atualizado}")
        
        return caminho_atualizado
        
    except Exception as e:
        logger.error(f"Erro ao atualizar modelo: {e}", exc_info=True)
        return None 