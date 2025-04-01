# -*- coding: utf-8 -*-

"""Pacote de dados do SigmaTrader"""

from .database import (
    inicializar_banco_dados,
    verificar_contas_existentes,
    listar_contas,
    verificar_email_existente,
    cadastrar_conta_db,
    obter_detalhes_conta,
    obter_nome_conta,
    deletar_conta_db,
    registrar_acesso,
    obter_saldos_conta,
    atualizar_saldos_conta,
    obter_id_conta_atual,
)

__all__ = [
    'inicializar_banco_dados',
    'verificar_contas_existentes',
    'listar_contas',
    'verificar_email_existente',
    'cadastrar_conta_db',
    'obter_detalhes_conta',
    'obter_nome_conta',
    'deletar_conta_db',
    'registrar_acesso',
    'obter_saldos_conta',
    'atualizar_saldos_conta',
    'obter_id_conta_atual',
] 