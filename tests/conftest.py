"""Fixtures compartilhadas.

Todos os payloads seguem o formato da API do Studeo, mas os valores são FALSOS.
Nenhum teste faz chamada real: as respostas são simuladas pelo pytest-httpx.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from apistudeo import StudeoClient, endpoints

FAKE_CPF = "00000000000"
FAKE_SENHA = "senha-falsa"
FAKE_TOKEN = "eyJ.fake.token"
FAKE_REFRESH = "eyJ.fake.refresh"

# 2026-03-02 10:00:00 e 2026-03-08 23:59:00 no horário de Brasília (UTC-3), em ms
INICIO_MS = 1772456400000
FIM_MS = 1773025140000


def api_url(path: str) -> str:
    return endpoints.BASE_URL + path


@pytest.fixture
def studeo() -> Iterator[StudeoClient]:
    """Cliente já autenticado com token falso e sem espera entre requests."""
    with StudeoClient.from_token(
        FAKE_TOKEN, refresh_token=FAKE_REFRESH, min_request_interval=0
    ) as client:
        yield client


@pytest.fixture
def studeo_login() -> Iterator[StudeoClient]:
    """Cliente com CPF e senha falsos, ainda sem token."""
    with StudeoClient(cpf=FAKE_CPF, senha=FAKE_SENHA, min_request_interval=0) as client:
        yield client


@pytest.fixture
def user_payload() -> dict[str, Any]:
    return {
        "id": 1001,
        "cdUsuario": "00000000-0",
        "nmUsuario": "Aluno Teste",
        "dsEmail": "aluno.teste@example.com",
        "dhUltimoAcesso": INICIO_MS,
        "nmPerfil": "ALUNO",
        "curso": None,
        "modalidade": None,
        "cpf": FAKE_CPF,
        "unidadeAssociada": {"id": 1, "nmUnidade": "Polo Teste"},
        "cursoList": [{"nmCurso": "Curso Teste", "cdCurso": "CURSO_TESTE"}],
    }


@pytest.fixture
def time_info_payload() -> dict[str, Any]:
    return {
        "datetime": "2026-03-02T10:00:00.000-0300",
        "offset": -180,
        "timezone": "-0300",
        "timezoneId": "America/Sao_Paulo",
        "timestamp": INICIO_MS,
    }


@pytest.fixture
def disciplines_payload() -> list[dict[str, Any]]:
    return [
        {
            "tpMatricula": "Matriculado",
            "tpDetalhe": "Curricular",
            "idDisciplina": 101,
            "nmDisciplina": "DISCIPLINA TESTE A",
            "cdShortname": "2026_TESTE_A",
            "flAtivo": True,
            "dhLiberar": None,
            "ano": 2026,
            "semestre": 51,
            "cdDisciplina": "TESTE_A",
            "cdTurma": "TURMA_TESTE",
            "flCurricular": True,
            "flDestaque": False,
            "flDigital": False,
        },
        {
            "tpMatricula": "Matriculado",
            "tpDetalhe": "Curricular",
            "idDisciplina": 102,
            "nmDisciplina": "DISCIPLINA TESTE B",
            "cdShortname": "2026_TESTE_B",
            "flAtivo": False,
            "ano": 2026,
            "semestre": 52,
            "cdDisciplina": "TESTE_B",
            "flCurricular": True,
        },
    ]


@pytest.fixture
def non_curricular_payload() -> list[dict[str, Any]]:
    return [
        {
            "tpMatricula": "MATRICULADO",
            "tpDetalhe": "Nao curricular",
            "idDisciplina": 901,
            "nmDisciplina": "ATIVIDADE COMPLEMENTAR TESTE",
            "cdShortname": "MDL_TESTE_901",
            "flAtivo": True,
            "ano": 2026,
            "semestre": 99,
            "cdDisciplina": "901",
            "flCurricular": False,
        }
    ]


@pytest.fixture
def study_plan_payload() -> list[dict[str, Any]]:
    return [
        {
            "dhInicial": INICIO_MS,
            "dhFinal": FIM_MS,
            "dsPlanoDeEstudoTipoEvento": "Aula",
            "dsPlanoDeEstudoSubTipoEvento": "AULA",
            "dsPlanoDeEstudoTipoAlerta": "Aula",
            "tpCor": "success",
            "nmDisciplina": "DISCIPLINA TESTE A",
            "cdShortname": "2026_TESTE_A",
        },
        {
            "dhInicial": INICIO_MS,
            "dhFinal": None,
            "dsPlanoDeEstudoTipoEvento": "Evento sem prazo",
            "nmDisciplina": "DISCIPLINA TESTE B",
            "cdShortname": "2026_TESTE_B",
        },
    ]


@pytest.fixture
def announcements_payload() -> list[dict[str, Any]]:
    return [
        {
            "id": 5001,
            "nmDestinatario": "Mediador Teste",
            "cdUsuario": None,
            "ultimoTexto": "<p>Olá, estudante! Aviso de teste.</p>",
            "dtTexto": INICIO_MS,
            "nLida": 1,
            "aba": "AVISO",
            "nmCategoria": "Categoria Teste",
            "nmConversaStatus": "Em andamento",
            "flPriorizar": False,
        },
        {
            "id": 5002,
            "nmDestinatario": "Mediador Teste",
            "ultimoTexto": "<p>Outro aviso de teste.</p>",
            "dtTexto": FIM_MS,
            "nLida": 0,
            "aba": "AVISO",
            "nmCategoria": "Categoria Teste",
            "nmConversaStatus": "Finalizada",
        },
    ]
