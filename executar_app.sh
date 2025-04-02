#!/bin/bash

# Configurar as variáveis de ambiente CUDA
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda/bin:$PATH

# Ativar o ambiente virtual Python
source venv/bin/activate

# Executar a aplicação
python app.py 