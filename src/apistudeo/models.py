"""Models pydantic v2 que traduzem o JSON da API do Studeo para nomes legíveis."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudeoModel(BaseModel):
    """Base dos models: aceita nome ou alias, ignora campos extras e guarda o JSON original."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    raw: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)

    @model_validator(mode="before")
    @classmethod
    def _keep_raw(cls, data: Any) -> Any:
        if isinstance(data, dict) and "raw" not in data:
            return {**data, "raw": dict(data)}
        return data


class AuthInfo(StudeoModel):
    """Tokens da sessão autenticada."""

    token: str = Field(repr=False)
    refresh_token: str | None = Field(default=None, alias="refreshToken", repr=False)
