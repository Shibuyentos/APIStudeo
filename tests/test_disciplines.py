"""Testes das disciplinas: model e métodos do cliente."""

from __future__ import annotations

import pytest
from conftest import FAKE_TOKEN, api_url
from pydantic import ValidationError
from pytest_httpx import HTTPXMock

from apistudeo import Discipline, StudeoClient, endpoints

URL_CURRICULARES = api_url(endpoints.DISCIPLINAS_CURRICULARES.format(curricular="true"))
URL_NAO_CURRICULARES = api_url(endpoints.DISCIPLINAS_CURRICULARES.format(curricular="false"))


class TestGetDisciplines:
    def test_curriculares(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, disciplines_payload: list[dict]
    ) -> None:
        httpx_mock.add_response(
            url=URL_CURRICULARES,
            method="GET",
            match_headers={"Authorization": FAKE_TOKEN},
            json=disciplines_payload,
        )

        disciplines = studeo.get_disciplines()

        assert [d.name for d in disciplines] == ["DISCIPLINA TESTE A", "DISCIPLINA TESTE B"]
        assert disciplines[1].is_active is False
        assert disciplines[0].raw == disciplines_payload[0]

    def test_nao_curriculares(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, non_curricular_payload: list[dict]
    ) -> None:
        httpx_mock.add_response(url=URL_NAO_CURRICULARES, json=non_curricular_payload)

        disciplines = studeo.get_disciplines(curricular=False)

        assert [d.id for d in disciplines] == [901]

    def test_todas_as_disciplinas(
        self,
        httpx_mock: HTTPXMock,
        studeo: StudeoClient,
        disciplines_payload: list[dict],
        non_curricular_payload: list[dict],
    ) -> None:
        httpx_mock.add_response(url=URL_CURRICULARES, json=disciplines_payload)
        httpx_mock.add_response(url=URL_NAO_CURRICULARES, json=non_curricular_payload)

        disciplines = studeo.get_all_disciplines()

        assert [d.id for d in disciplines] == [101, 102, 901]

    def test_sem_conteudo_vira_lista_vazia(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=URL_CURRICULARES, status_code=204)

        assert studeo.get_disciplines() == []


class TestDisciplineModel:
    def test_parse_curricular(self, disciplines_payload: list[dict]) -> None:
        discipline = Discipline.model_validate(disciplines_payload[0])

        assert discipline.id == 101
        assert discipline.name == "DISCIPLINA TESTE A"
        assert discipline.code == "TESTE_A"
        assert discipline.shortname == "2026_TESTE_A"
        assert discipline.year == 2026
        assert discipline.semester == 51
        assert discipline.is_curricular is True
        assert discipline.is_active is True
        assert discipline.enrollment_type == "Matriculado"
        assert discipline.detail_type == "Curricular"
        assert discipline.raw == disciplines_payload[0]

    def test_parse_nao_curricular(self, non_curricular_payload: list[dict]) -> None:
        discipline = Discipline.model_validate(non_curricular_payload[0])

        assert discipline.is_curricular is False
        assert discipline.semester == 99

    def test_padroes_dos_campos_opcionais(self) -> None:
        discipline = Discipline.model_validate({"idDisciplina": 1, "nmDisciplina": "X"})

        assert discipline.code is None
        assert discipline.year is None
        assert discipline.is_curricular is False
        assert discipline.is_active is True

    def test_dump_usa_nomes_legiveis_e_esconde_o_raw(self, disciplines_payload: list[dict]) -> None:
        discipline = Discipline.model_validate(disciplines_payload[0])

        dump = discipline.model_dump()

        assert dump["name"] == "DISCIPLINA TESTE A"
        assert "nmDisciplina" not in dump
        assert "raw" not in dump
        assert "raw" not in repr(discipline)

    def test_aceita_nome_do_campo_alem_do_alias(self) -> None:
        discipline = Discipline(id=1, name="X", is_active=False)

        assert (discipline.id, discipline.name, discipline.is_active) == (1, "X", False)

    def test_sem_campo_obrigatorio_e_invalido(self) -> None:
        with pytest.raises(ValidationError):
            Discipline.model_validate({"idDisciplina": 1})
