"""Funções auxiliares da APIStudeo."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from apistudeo.models import Grade

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def ms_to_datetime(value: int | float | datetime | None) -> datetime | None:
    """Converte um timestamp em milissegundos (padrão da API) para datetime em America/Sao_Paulo."""
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"timestamp em milissegundos inválido: {value!r}")
    try:
        return (_EPOCH + timedelta(milliseconds=value)).astimezone(SAO_PAULO)
    except OverflowError as exc:
        raise ValueError(f"timestamp em milissegundos fora do intervalo: {value!r}") from exc


def calculate_average(grades: Iterable[Grade]) -> float | None:
    """Calcula a média ponderada das notas, ou a simples se faltar algum peso.

    Notas sem valor são ignoradas. Devolve None se não houver nota válida.
    """
    graded = [grade for grade in grades if grade.value is not None]
    if not graded:
        return None
    if all(grade.weight is not None for grade in graded):
        total_weight = sum(grade.weight or 0 for grade in graded)
        if total_weight == 0:
            return None
        weighted = sum((grade.value or 0) * (grade.weight or 0) for grade in graded)
        return round(weighted / total_weight, 2)
    return round(sum(grade.value or 0 for grade in graded) / len(graded), 2)


def mask_cpf(cpf: str) -> str:
    """Mascara o CPF para log, mantendo só os 4 últimos dígitos."""
    return f"***{cpf[-4:]}" if len(cpf) >= 4 else "****"


def mask_token(token: str) -> str:
    """Mascara o token para log, mantendo só os primeiros caracteres."""
    return f"{token[:10]}..." if len(token) > 20 else "***"
