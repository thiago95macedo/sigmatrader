"""
Pacote de integração com a plataforma IQ Option
"""

from .login import LoginIQOption
# from .ativos import listar_ativos_abertos # Comentado/Removido
from .ativos import listar_ativos_abertos_com_payout # Adicionado

# Versão do pacote
__version__ = "2025.1.0.2"

__all__ = [
    "LoginIQOption",
    # "listar_ativos_abertos", # Comentado/Removido
    "listar_ativos_abertos_com_payout", # Adicionado
] 