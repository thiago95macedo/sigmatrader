"""
Pacote de integração com a plataforma IQ Option
"""

from .login import LoginIQOption
from .ativos import listar_ativos_abertos

# Versão do pacote
__version__ = "2025.1.0.1"

__all__ = [
    "LoginIQOption",
    "listar_ativos_abertos",
] 