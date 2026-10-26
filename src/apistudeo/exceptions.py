"""Exceções da APIStudeo.

Hierarquia::

    StudeoError
    ├── AuthenticationError
    └── StudeoAPIError
        └── RateLimitError
"""

from __future__ import annotations

MAX_RESPONSE_TEXT = 500


class StudeoError(Exception):
    """Erro base da lib. Também cobre falhas de conexão com a API."""


class AuthenticationError(StudeoError):
    """Login recusado, token ausente/expirado ou falha ao renovar o token."""


class StudeoAPIError(StudeoError):
    """A API respondeu com erro HTTP ou com um conteúdo fora do formato esperado."""

    def __init__(self, message: str, *, status_code: int, response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text[:MAX_RESPONSE_TEXT]


class RateLimitError(StudeoAPIError):
    """A API respondeu 429 (muitas requisições em pouco tempo)."""
