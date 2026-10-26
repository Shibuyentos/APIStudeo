"""Funções auxiliares da APIStudeo."""

from __future__ import annotations


def mask_cpf(cpf: str) -> str:
    """Mascara o CPF para log, mantendo só os 4 últimos dígitos."""
    return f"***{cpf[-4:]}" if len(cpf) >= 4 else "****"


def mask_token(token: str) -> str:
    """Mascara o token para log, mantendo só os primeiros caracteres."""
    return f"{token[:10]}..." if len(token) > 20 else "***"
