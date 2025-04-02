#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar a disponibilidade da GPU para o TensorFlow (versão simplificada).
"""

import os
import sys
import time
import tensorflow as tf

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== TESTE DE GPU PARA TENSORFLOW (SIMPLES) ===")

# Verificar versão do TensorFlow
print(f"Versão do TensorFlow: {tf.__version__}")

# Verificar disponibilidade de GPU
gpus = tf.config.list_physical_devices('GPU')
print(f"GPUs disponíveis: {gpus}")

# Verificar dispositivos lógicos
print(f"Dispositivos lógicos: {tf.config.list_logical_devices()}")

# Teste simples
print("\nExecutando teste simples...")

# Criar matrizes pequenas
a = tf.constant([[1.0, 2.0], [3.0, 4.0]])
b = tf.constant([[5.0, 6.0], [7.0, 8.0]])

# Teste na CPU
print("Teste na CPU:")
with tf.device('/CPU:0'):
    start = time.time()
    c_cpu = tf.matmul(a, b)
    end = time.time()
    print(f"Resultado: {c_cpu}")
    print(f"Tempo: {(end - start)*1000:.2f} ms")

# Teste na GPU (se disponível)
if gpus:
    print("\nTeste na GPU:")
    with tf.device('/GPU:0'):
        start = time.time()
        c_gpu = tf.matmul(a, b)
        end = time.time()
        print(f"Resultado: {c_gpu}")
        print(f"Tempo: {(end - start)*1000:.2f} ms")

print("\n=== TESTE CONCLUÍDO ===") 