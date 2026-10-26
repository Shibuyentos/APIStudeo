"""Models pydantic v2 que traduzem o JSON da API do Studeo para nomes legíveis."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from apistudeo.utils import ms_to_datetime

TimestampMs = Annotated[datetime, BeforeValidator(ms_to_datetime)]
"""Timestamp em milissegundos convertido para datetime em America/Sao_Paulo."""


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


class ServerTime(StudeoModel):
    """Hora do servidor do Studeo."""

    now: TimestampMs = Field(alias="timestamp")
    timezone_id: str | None = Field(default=None, alias="timezoneId")
    offset_minutes: int | None = Field(default=None, alias="offset")


class Course(StudeoModel):
    """Curso em que o aluno está matriculado."""

    name: str | None = Field(default=None, alias="nmCurso")
    code: str | None = Field(default=None, alias="cdCurso")


class User(StudeoModel):
    """Dados do usuário logado. CPF e e-mail ficam fora do repr."""

    id: int
    user_code: str | None = Field(default=None, alias="cdUsuario")
    name: str | None = Field(default=None, alias="nmUsuario")
    email: str | None = Field(default=None, alias="dsEmail", repr=False)
    cpf: str | None = Field(default=None, repr=False)
    profile: str | None = Field(default=None, alias="nmPerfil")
    last_access_at: TimestampMs | None = Field(default=None, alias="dhUltimoAcesso")
    courses: list[Course] = Field(default_factory=list, alias="cursoList")

    @field_validator("courses", mode="before")
    @classmethod
    def _null_as_empty(cls, value: Any) -> Any:
        return [] if value is None else value

    @property
    def course_name(self) -> str | None:
        """Nome do primeiro curso da lista."""
        return self.courses[0].name if self.courses else None


class Discipline(StudeoModel):
    """Disciplina do aluno."""

    id: int = Field(alias="idDisciplina")
    name: str = Field(alias="nmDisciplina")
    code: str | None = Field(default=None, alias="cdDisciplina")
    shortname: str | None = Field(default=None, alias="cdShortname")
    year: int | None = Field(default=None, alias="ano")
    semester: int | None = Field(
        default=None, alias="semestre", description="51, 52; 99 = especial"
    )
    is_curricular: bool = Field(default=False, alias="flCurricular")
    is_active: bool = Field(default=True, alias="flAtivo")
    enrollment_type: str | None = Field(default=None, alias="tpMatricula")
    detail_type: str | None = Field(default=None, alias="tpDetalhe")


class StudyEvent(StudeoModel):
    """Evento do plano de estudo."""

    discipline_name: str = Field(alias="nmDisciplina")
    shortname: str | None = Field(default=None, alias="cdShortname")
    event_type: str | None = Field(default=None, alias="dsPlanoDeEstudoTipoEvento")
    sub_type: str | None = Field(default=None, alias="dsPlanoDeEstudoSubTipoEvento")
    alert_type: str | None = Field(default=None, alias="dsPlanoDeEstudoTipoAlerta")
    color: str | None = Field(default=None, alias="tpCor")
    start_at: TimestampMs | None = Field(default=None, alias="dhInicial")
    end_at: TimestampMs | None = Field(default=None, alias="dhFinal")


class Announcement(StudeoModel):
    """Aviso ou comunicado do mediador."""

    id: int
    sender_name: str | None = Field(default=None, alias="nmDestinatario")
    text: str | None = Field(default=None, alias="ultimoTexto", description="Conteúdo em HTML")
    category: str | None = Field(default=None, alias="nmCategoria")
    sent_at: TimestampMs | None = Field(default=None, alias="dtTexto")
    is_unread: bool = Field(default=False, alias="nLida")
    status: str | None = Field(default=None, alias="nmConversaStatus")

    @field_validator("is_unread", mode="before")
    @classmethod
    def _flag_to_bool(cls, value: Any) -> bool:
        return bool(value)


class Deadline(StudeoModel):
    """Prazo derivado de um evento do plano de estudo."""

    discipline_name: str
    discipline_code: str | None = None
    type: str = ""
    title: str = ""
    due_date: datetime | None = None
    status: str = "pendente"

    @classmethod
    def from_study_event(cls, event: StudyEvent) -> Deadline:
        """Converte um evento do plano de estudo em prazo, com a mesma regra do Bot-Studeo."""
        kind = event.sub_type or event.event_type or ""
        title = (
            f"{event.event_type} — {event.discipline_name}"
            if event.event_type
            else event.discipline_name
        )
        return cls(
            discipline_name=event.discipline_name,
            discipline_code=event.shortname,
            type=kind.lower(),
            title=title,
            due_date=event.end_at,
            raw=event.raw,
        )


class Grade(StudeoModel):
    """Nota de uma avaliação. Experimental: o endpoint de notas ainda não foi mapeado."""

    discipline_name: str
    discipline_code: str | None = None
    type: str = ""
    value: float | None = None
    weight: float | None = None
    recorded_at: datetime | None = None


class _PendingCount(StudeoModel):
    total: int = Field(default=0, alias="somaTotal")


class _UnreadCount(StudeoModel):
    count: int = Field(default=0, alias="qtdMensagem")
