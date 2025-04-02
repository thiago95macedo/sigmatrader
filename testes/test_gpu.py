#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar a disponibilidade e desempenho da GPU para o TensorFlow.
"""

import os
import sys
import time
import logging
import numpy as np
import tensorflow as tf

# Configuração de diretórios
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(TESTS_DIR, 'logs')

# Criar diretório de logs se não existir
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'gpu_benchmark.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GPUTest')

def testar_gpu():
    """
    Testa a disponibilidade e o desempenho da GPU para o TensorFlow.
    """
    logger.info("=== TESTE DE GPU PARA TENSORFLOW ===")
    
    # Verificar disponibilidade de GPU
    logger.info("Verificando GPUs disponíveis...")
    gpus = tf.config.list_physical_devices('GPU')
    
    if not gpus:
        logger.warning("Nenhuma GPU encontrada. O TensorFlow está usando apenas a CPU.")
    else:
        for gpu in gpus:
            logger.info(f"GPU encontrada: {gpu}")
        
    # Registrar informações da versão do TensorFlow
    logger.info(f"Versão do TensorFlow: {tf.__version__}")
    logger.info(f"Dispositivos disponíveis: {tf.config.list_logical_devices()}")
    
    # Testar desempenho da GPU vs CPU
    logger.info("\n=== TESTE DE DESEMPENHO ===")
    
    # Tamanho das matrizes para teste
    matrix_size = 1000  # Reduzido para teste mais rápido
    logger.info(f"Realizando multiplicação de matrizes {matrix_size}x{matrix_size}")
    
    # Criar matrizes aleatórias grandes
    A = tf.random.normal((matrix_size, matrix_size))
    B = tf.random.normal((matrix_size, matrix_size))
    
    # Testar na CPU
    logger.info("Executando multiplicação de matrizes na CPU...")
    with tf.device('/CPU:0'):
        start_time = time.time()
        result_cpu = tf.matmul(A, B)
        # Forçar execução
        result_cpu = result_cpu.numpy()
        cpu_time = time.time() - start_time
    
    logger.info(f"Tempo de execução na CPU: {cpu_time:.4f} segundos")
    
    # Testar na GPU (se disponível)
    if gpus:
        logger.info("Executando multiplicação de matrizes na GPU...")
        with tf.device('/GPU:0'):
            start_time = time.time()
            result_gpu = tf.matmul(A, B)
            # Forçar execução
            result_gpu = result_gpu.numpy()
            gpu_time = time.time() - start_time
        
        logger.info(f"Tempo de execução na GPU: {gpu_time:.4f} segundos")
        
        if cpu_time > 0:
            speedup = cpu_time / gpu_time
            logger.info(f"Aceleração com GPU: {speedup:.2f}x mais rápido")
    
    logger.info("Teste de GPU concluído!")

if __name__ == "__main__":
    testar_gpu() 