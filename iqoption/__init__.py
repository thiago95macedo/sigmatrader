"""
SigmaTrader - Módulo IQ Option
Funções e classes para interação com a API da IQ Option
"""

from .login import LoginIQOption
from .ativos import listar_ativos_abertos_com_payout

__all__ = ['LoginIQOption', 'listar_ativos_abertos_com_payout'] 