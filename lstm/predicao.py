"""
Módulo para predição e operação usando modelos LSTM
"""

import os
import time
import logging
import tensorflow as tf
import numpy as np
import pandas as pd
import datetime
from .preprocessamento import preparar_dados_predicao

logger = logging.getLogger(__name__)

def carregar_modelo(caminho_modelo):
    """
    Carrega um modelo LSTM salvo
    
    Args:
        caminho_modelo: Caminho para o arquivo do modelo
        
    Returns:
        Modelo carregado ou None em caso de erro
    """
    logger.info(f"Carregando modelo de {caminho_modelo}")
    
    # Verificar se o arquivo existe
    if not os.path.exists(caminho_modelo):
        logger.error(f"Arquivo de modelo não encontrado: {caminho_modelo}")
        return None
    
    # Verificar se o arquivo tem tamanho válido
    if os.path.getsize(caminho_modelo) < 1000:  # Um modelo válido normalmente tem pelo menos alguns KB
        logger.error(f"Arquivo de modelo aparenta estar corrompido (tamanho muito pequeno): {caminho_modelo}")
        return None
        
    try:
        modelo = tf.keras.models.load_model(caminho_modelo)
        return modelo
    except OSError as e:
        if "file signature not found" in str(e):
            logger.error(f"Erro ao carregar o modelo: O arquivo está corrompido ou em formato inválido")
            # Recomendação para o usuário
            logger.info(f"Recomendação: Treine um novo modelo, pois o atual ({os.path.basename(caminho_modelo)}) está corrompido")
        else:
            logger.error(f"Erro ao carregar o modelo: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao carregar o modelo: {e}")
        return None

def fazer_predicao(modelo, X_pred):
    """
    Realiza uma predição usando o modelo carregado
    
    Args:
        modelo: Modelo LSTM carregado
        X_pred: Dados formatados para entrada no modelo
        
    Returns:
        Tuple (int, float): (direção prevista (0=PUT, 1=CALL), confiança da previsão)
    """
    logger.info("Realizando predição com o modelo LSTM")
    
    try:
        # Obter a predição bruta
        predicao = modelo.predict(X_pred)
        
        # Obter a classe prevista (0=PUT, 1=CALL)
        classe_prevista = np.argmax(predicao[0])
        
        # Obter a confiança da previsão
        confianca = predicao[0][classe_prevista] * 100
        
        logger.info(f"Predição: {'CALL' if classe_prevista == 1 else 'PUT'} com {confianca:.2f}% de confiança")
        
        return classe_prevista, confianca
    except Exception as e:
        logger.error(f"Erro durante a predição: {e}", exc_info=True)
        return None, 0

def realizar_operacao(api_iq, direcao, valor, ativo, expiracao=1):
    """
    Realiza uma operação na IQ Option
    
    Args:
        api_iq: API IQ Option conectada
        direcao: Direção da operação (0=PUT, 1=CALL)
        valor: Valor da operação
        ativo: Ativo a operar
        expiracao: Tempo de expiração em minutos (padrão = 1)
        
    Returns:
        tuple: (status da operação, id da operação, resultado)
    """
    tipo_operacao = "call" if direcao == 1 else "put"
    logger.info(f"Realizando operação: {tipo_operacao.upper()} em {ativo} - Valor: {valor}")
    
    try:
        # Verifica se está perto do fechamento do minuto
        agora = datetime.datetime.now()
        segundos = agora.second
        
        # Se estiver nos últimos 10 segundos do minuto, aguarda para o próximo
        if segundos >= 50:
            tempo_espera = 60 - segundos + 1
            logger.info(f"Aguardando {tempo_espera} segundos para o próximo minuto")
            time.sleep(tempo_espera)
        
        # Executa a operação
        status, id_operacao = api_iq.buy(valor, ativo, tipo_operacao, expiracao)
        
        if not status:
            logger.error(f"Falha ao executar operação: {id_operacao}")
            return False, None, None
        
        logger.info(f"Operação iniciada com ID {id_operacao}")
        
        # Aguarda o resultado
        resultado = None
        
        if expiracao == 1:
            # Tempo estimado para aguardar resultado (1 minuto + 10 segundos)
            tempo_maximo = 70
            inicio = time.time()
            
            while time.time() - inicio < tempo_maximo:
                try:
                    resultado, lucro = api_iq.check_win_v4(id_operacao)
                    if resultado:
                        logger.info(f"Operação finalizada: {resultado} - Lucro: {lucro}")
                        return True, id_operacao, resultado
                except Exception as e:
                    logger.warning(f"Erro ao verificar resultado: {e}")
                
                time.sleep(1)
            
            logger.warning("Tempo limite excedido para verificar resultado")
            return True, id_operacao, "timeout"
        else:
            # Para operações com expiração maior, só inicia e não aguarda
            return True, id_operacao, None
    
    except Exception as e:
        logger.error(f"Erro ao realizar operação: {e}", exc_info=True)
        return False, None, None

def calcular_indicadores_tecnicos(api_iq, ativo):
    """
    Calcula indicadores técnicos adicionais para análise
    
    Args:
        api_iq: API IQ Option conectada
        ativo: Ativo para analisar
        
    Returns:
        dict: Dicionário com os indicadores calculados
    """
    try:
        # Obtém as velas mais recentes
        candles = api_iq.get_candles(ativo, 60, 50, time.time())
        if not candles:
            return {}
        
        # Cria o DataFrame
        df = pd.DataFrame()
        for candle in candles:
            df = pd.concat([df, pd.DataFrame([candle])], ignore_index=True)
        
        # Extrai preços de fechamento
        fechamento = df['close'].values
        
        # Calcula indicadores
        indicadores = {}
        
        # Tendência baseada nas últimas 3 velas
        if len(fechamento) >= 3:
            tendencia = "LATERAL"
            if fechamento[-1] > fechamento[-2] > fechamento[-3]:
                tendencia = "ALTA"
            elif fechamento[-1] < fechamento[-2] < fechamento[-3]:
                tendencia = "BAIXA"
            indicadores["tendencia"] = tendencia
        
        # Média móvel de 20 períodos
        if len(fechamento) >= 20:
            mm20 = np.mean(fechamento[-20:])
            indicadores["MM20"] = round(mm20, 5)
            
            # Posição do preço em relação à MM20
            preco_atual = fechamento[-1]
            indicadores["Preço vs MM20"] = "ACIMA" if preco_atual > mm20 else "ABAIXO"
        
        # RSI
        if len(fechamento) >= 14:
            delta = np.diff(fechamento)
            ganho = np.where(delta > 0, delta, 0)
            perda = np.where(delta < 0, -delta, 0)
            
            # Média dos ganhos e perdas
            media_ganho = np.mean(ganho[-14:])
            media_perda = np.mean(perda[-14:])
            
            if media_perda != 0:
                rs = media_ganho / media_perda
                rsi = 100 - (100 / (1 + rs))
                indicadores["RSI"] = round(rsi, 2)
                
                # Interpretação do RSI
                if rsi >= 70:
                    indicadores["RSI_status"] = "SOBRECOMPRADO"
                elif rsi <= 30:
                    indicadores["RSI_status"] = "SOBREVENDIDO"
                else:
                    indicadores["RSI_status"] = "NEUTRO"
        
        return indicadores
        
    except Exception as e:
        logger.error(f"Erro ao calcular indicadores técnicos: {e}", exc_info=True)
        return {}

def analisar_ativo_lstm(api_iq, caminho_modelo, ativo):
    """
    Analisa um ativo usando o modelo LSTM e retorna a previsão
    
    Args:
        api_iq: API IQ Option conectada
        caminho_modelo: Caminho para o modelo treinado
        ativo: Ativo para analisar
        
    Returns:
        dict: Resultado da análise com a previsão e indicadores, ou None em caso de erro
    """
    logger.info(f"Analisando ativo {ativo} com modelo LSTM")
    
    try:
        # 1. Verificar se o arquivo existe
        if not os.path.exists(caminho_modelo):
            logger.error(f"Modelo não encontrado no caminho: {caminho_modelo}")
            return {
                'erro': True,
                'mensagem': f"Modelo não encontrado. Você precisa treinar um modelo primeiro.",
                'tipo_erro': 'arquivo_nao_encontrado'
            }
        
        # 2. Carregar o modelo
        modelo = carregar_modelo(caminho_modelo)
        if modelo is None:
            logger.error(f"Falha ao carregar o modelo: {caminho_modelo}")
            return {
                'erro': True,
                'mensagem': f"O modelo parece estar corrompido. Tente treinar um novo modelo.",
                'tipo_erro': 'modelo_corrompido'
            }
        
        # 3. Preparar os dados para predição
        X_pred = preparar_dados_predicao(api_iq, ativo)
        if X_pred is None:
            logger.error("Falha ao preparar dados para predição")
            return {
                'erro': True,
                'mensagem': f"Não foi possível preparar os dados para predição. Verifique a conexão com a IQ Option.",
                'tipo_erro': 'falha_dados'
            }
        
        # 4. Fazer a predição
        direcao, confianca = fazer_predicao(modelo, X_pred)
        if direcao is None:
            return {
                'erro': True,
                'mensagem': f"Falha ao executar a predição com o modelo.",
                'tipo_erro': 'falha_predicao'
            }
        
        # 5. Calcular indicadores técnicos adicionais
        indicadores = calcular_indicadores_tecnicos(api_iq, ativo)
        
        # 6. Retornar o resultado completo
        resultado = {
            'erro': False,
            'ativo': ativo,
            'direcao': 'call' if direcao == 1 else 'put',
            'confianca': confianca,
            'indicadores': indicadores,
            'timestamp': time.time(),
            'modelo': os.path.basename(caminho_modelo)
        }
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao analisar ativo: {e}", exc_info=True)
        return {
            'erro': True,
            'mensagem': f"Erro inesperado durante análise: {str(e)}",
            'tipo_erro': 'excecao'
        }

def executar_operacoes_lstm(api_iq, caminho_modelo, ativo, valor_operacao, num_operacoes=0):
    """
    Executa operações automáticas usando modelo LSTM
    
    Args:
        api_iq: API IQ Option conectada
        caminho_modelo: Caminho para o modelo treinado
        ativo: Ativo para operar
        valor_operacao: Valor de cada operação
        num_operacoes: Número de operações (0 = contínuo até interrupção)
        
    Returns:
        dict: Resumo das operações realizadas ou mensagem de erro
    """
    logger.info(f"Iniciando operações automáticas em {ativo} com modelo LSTM")
    
    # Verificar se o arquivo existe
    if not os.path.exists(caminho_modelo):
        logger.error(f"Modelo não encontrado no caminho: {caminho_modelo}")
        return {
            'erro': True,
            'mensagem': f"Modelo não encontrado. Você precisa treinar um modelo primeiro.",
            'tipo_erro': 'arquivo_nao_encontrado'
        }
    
    # Carrega o modelo
    modelo = carregar_modelo(caminho_modelo)
    if modelo is None:
        logger.error(f"Falha ao carregar o modelo: {caminho_modelo}")
        return {
            'erro': True,
            'mensagem': f"O modelo parece estar corrompido. Tente treinar um novo modelo.",
            'tipo_erro': 'modelo_corrompido'
        }
    
    # Estatísticas
    operacoes_realizadas = 0
    operacoes_win = 0
    operacoes_loss = 0
    operacoes_empate = 0
    
    # Hora de início
    hora_inicio = time.time()
    
    try:
        # Loop de operações
        continuar = True
        while continuar:
            if num_operacoes > 0 and operacoes_realizadas >= num_operacoes:
                logger.info(f"Número máximo de operações atingido: {num_operacoes}")
                break
            
            # Verificar horário de operação
            hora_atual = datetime.datetime.now().hour
            if hora_atual < 8 or hora_atual > 20:  # Evita operar em horários de baixa liquidez
                logger.warning(f"Fora do horário ideal para operações: {hora_atual}h. Aguardando 5 minutos.")
                time.sleep(300)  # Espera 5 minutos
                continue
            
            # Preparar os dados para predição
            X_pred = preparar_dados_predicao(api_iq, ativo)
            if X_pred is None:
                logger.error("Falha ao preparar dados para predição. Aguardando 1 minuto.")
                time.sleep(60)
                continue
            
            # Fazer a predição
            direcao, confianca = fazer_predicao(modelo, X_pred)
            if direcao is None:
                logger.error("Falha na predição. Aguardando 1 minuto.")
                time.sleep(60)
                continue
            
            # Verificar nível de confiança mínimo (70%)
            if confianca < 70.0:
                logger.info(f"Confiança insuficiente para operar: {confianca:.2f}%. Aguardando 30 segundos.")
                time.sleep(30)
                continue
            
            # Executar a operação
            tipo_operacao = "call" if direcao == 1 else "put"
            logger.info(f"Executando operação: {tipo_operacao.upper()} em {ativo} - Valor: {valor_operacao} - Confiança: {confianca:.2f}%")
            
            # Expiracao fixa em 1 minuto
            expiracao = 1
            
            # Realiza a operação
            sucesso, id_op, resultado = realizar_operacao(api_iq, direcao, valor_operacao, ativo, expiracao)
            
            if sucesso:
                operacoes_realizadas += 1
                
                # Verifica o resultado
                if resultado == "win":
                    operacoes_win += 1
                elif resultado == "loose":
                    operacoes_loss += 1
                elif resultado == "equal":
                    operacoes_empate += 1
                
                # Exibe estatísticas
                taxa_acertos = (operacoes_win / operacoes_realizadas) * 100 if operacoes_realizadas > 0 else 0
                logger.info(f"Estatísticas: Win: {operacoes_win}, Loss: {operacoes_loss}, Empate: {operacoes_empate}")
                logger.info(f"Taxa de acertos: {taxa_acertos:.2f}%")
                
                # Aguarda 30 segundos antes da próxima operação
                time.sleep(30)
            else:
                # Em caso de falha, aguarda um pouco mais (1 minuto)
                logger.warning("Falha ao executar operação. Aguardando 1 minuto.")
                time.sleep(60)
        
        # Resumo final
        tempo_total = time.time() - hora_inicio
        horas = int(tempo_total // 3600)
        minutos = int((tempo_total % 3600) // 60)
        segundos = int(tempo_total % 60)
        
        logger.info(f"Operações finalizadas: {operacoes_realizadas}")
        logger.info(f"Tempo total: {horas}h {minutos}m {segundos}s")
        
        if operacoes_realizadas > 0:
            taxa_acertos = (operacoes_win / operacoes_realizadas) * 100
            logger.info(f"Taxa final de acertos: {taxa_acertos:.2f}%")
        
        return {
            'erro': False,
            'total_operacoes': operacoes_realizadas,
            'wins': operacoes_win,
            'losses': operacoes_loss,
            'ties': operacoes_empate,
            'taxa_acerto': (operacoes_win / operacoes_realizadas * 100) if operacoes_realizadas > 0 else 0,
            'tempo_total_segundos': tempo_total
        }
    
    except KeyboardInterrupt:
        # Resumo em caso de interrupção
        logger.info("Operações interrompidas pelo usuário")
        tempo_total = time.time() - hora_inicio
        
        return {
            'erro': False,
            'interrompido': True,
            'total_operacoes': operacoes_realizadas,
            'wins': operacoes_win,
            'losses': operacoes_loss,
            'ties': operacoes_empate,
            'taxa_acerto': (operacoes_win / operacoes_realizadas * 100) if operacoes_realizadas > 0 else 0,
            'tempo_total_segundos': tempo_total
        }
        
    except Exception as e:
        logger.error(f"Erro nas operações automáticas: {e}", exc_info=True)
        
        return {
            'erro': True,
            'mensagem': f"Erro durante operações automáticas: {str(e)}",
            'tipo_erro': 'excecao',
            'total_operacoes': operacoes_realizadas,
            'wins': operacoes_win,
            'losses': operacoes_loss,
            'ties': operacoes_empate
        } 