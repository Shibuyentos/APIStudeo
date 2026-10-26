"""Testes de plano de estudo, prazos, avisos, contadores, notas e utilitários."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest
from conftest import FIM_MS, INICIO_MS, api_url
from pytest_httpx import HTTPXMock

from apistudeo import Announcement, Deadline, Grade, StudeoClient, StudyEvent, endpoints
from apistudeo.utils import SAO_PAULO, calculate_average, ms_to_datetime

URL_PLANO = api_url(endpoints.PLANO_ESTUDO_DISCIPLINAS)
URL_NAO_LIDAS = api_url(endpoints.MENSAGENS_NAO_LIDAS)
URL_AFAZER = api_url(endpoints.DISCIPLINAS_AFAZER)


def url_avisos(page_size: int) -> httpx.URL:
    params = {
        "aba": "AVISO",
        "mediador": "false",
        "novasPrimeiro": "true",
        "pageOffset": str(page_size),
        "startIndex": "0",
    }
    return httpx.URL(api_url(endpoints.ATENDIMENTO_LISTA), params=params)


class TestGetStudyPlanEDeadlines:
    def test_get_study_plan(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, study_plan_payload: list[dict]
    ) -> None:
        httpx_mock.add_response(url=URL_PLANO, json=study_plan_payload)

        events = studeo.get_study_plan()

        assert [e.discipline_name for e in events] == ["DISCIPLINA TESTE A", "DISCIPLINA TESTE B"]
        assert events[0].raw == study_plan_payload[0]

    def test_plano_vazio_responde_204(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=URL_PLANO, status_code=204)

        assert studeo.get_study_plan() == []

    def test_get_deadlines_ignora_eventos_sem_data_final(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, study_plan_payload: list[dict]
    ) -> None:
        httpx_mock.add_response(url=URL_PLANO, json=study_plan_payload)

        deadlines = studeo.get_deadlines()

        assert len(deadlines) == 1
        assert deadlines[0].title == "Aula — DISCIPLINA TESTE A"
        assert deadlines[0].due_date == datetime(2026, 3, 8, 23, 59, tzinfo=SAO_PAULO)


class TestGetAnnouncements:
    def test_parametros_e_parse(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, announcements_payload: list[dict]
    ) -> None:
        httpx_mock.add_response(url=url_avisos(7), json=announcements_payload)

        announcements = studeo.get_announcements()

        assert [a.id for a in announcements] == [5001, 5002]
        assert [a.is_unread for a in announcements] == [True, False]

    def test_page_size(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=url_avisos(20), json=[])

        assert studeo.get_announcements(page_size=20) == []

    def test_page_size_invalido(self, studeo: StudeoClient) -> None:
        with pytest.raises(ValueError, match="page_size"):
            studeo.get_announcements(page_size=0)


class TestContadores:
    def test_nao_lidas_soma_todas_as_situacoes(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(
            url=URL_NAO_LIDAS,
            json=[
                {"situacao": "COMUNICADO", "qtdMensagem": 5},
                {"situacao": "MENSAGEM", "qtdMensagem": 2},
            ],
        )

        assert studeo.get_unread_count() == 7

    def test_pendencias(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=URL_AFAZER, json={"somaTotal": 12})

        assert studeo.get_pending_count() == 12

    @pytest.mark.parametrize("metodo", ["get_unread_count", "get_pending_count"])
    def test_sem_conteudo_vira_zero(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, metodo: str
    ) -> None:
        url = URL_NAO_LIDAS if metodo == "get_unread_count" else URL_AFAZER
        httpx_mock.add_response(url=url, status_code=204)

        assert getattr(studeo, metodo)() == 0


class TestGetGrades:
    def test_experimental_avisa_e_devolve_lista_vazia(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        with pytest.warns(UserWarning, match="experimental"):
            assert studeo.get_grades() == []

        assert httpx_mock.get_requests() == []


class TestStudyEventModel:
    def test_parse(self, study_plan_payload: list[dict]) -> None:
        event = StudyEvent.model_validate(study_plan_payload[0])

        assert event.discipline_name == "DISCIPLINA TESTE A"
        assert event.shortname == "2026_TESTE_A"
        assert event.event_type == "Aula"
        assert event.sub_type == "AULA"
        assert event.alert_type == "Aula"
        assert event.color == "success"
        assert event.start_at == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert event.end_at == datetime(2026, 3, 8, 23, 59, tzinfo=SAO_PAULO)
        assert event.start_at < event.end_at

    def test_evento_sem_data_final(self, study_plan_payload: list[dict]) -> None:
        event = StudyEvent.model_validate(study_plan_payload[1])

        assert event.end_at is None
        assert event.sub_type is None


class TestAnnouncementModel:
    def test_parse(self, announcements_payload: list[dict]) -> None:
        announcement = Announcement.model_validate(announcements_payload[0])

        assert announcement.id == 5001
        assert announcement.sender_name == "Mediador Teste"
        assert announcement.text == "<p>Olá, estudante! Aviso de teste.</p>"
        assert announcement.category == "Categoria Teste"
        assert announcement.sent_at == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert announcement.status == "Em andamento"

    @pytest.mark.parametrize(("n_lida", "nao_lida"), [(1, True), (0, False), (None, False)])
    def test_nlida_indica_aviso_nao_lido(
        self, announcements_payload: list[dict], n_lida: int | None, nao_lida: bool
    ) -> None:
        payload = {**announcements_payload[0], "nLida": n_lida}

        assert Announcement.model_validate(payload).is_unread is nao_lida


class TestDeadlineModel:
    def test_from_study_event(self, study_plan_payload: list[dict]) -> None:
        event = StudyEvent.model_validate(study_plan_payload[0])

        deadline = Deadline.from_study_event(event)

        assert deadline.discipline_name == "DISCIPLINA TESTE A"
        assert deadline.discipline_code == "2026_TESTE_A"
        assert deadline.type == "aula"
        assert deadline.title == "Aula — DISCIPLINA TESTE A"
        assert deadline.due_date == event.end_at
        assert deadline.status == "pendente"
        assert deadline.raw == study_plan_payload[0]

    def test_tipo_usa_o_tipo_do_evento_quando_falta_subtipo(self) -> None:
        event = StudyEvent(discipline_name="X", event_type="Prova", end_at=FIM_MS)

        assert Deadline.from_study_event(event).type == "prova"

    def test_titulo_sem_tipo_de_evento(self) -> None:
        event = StudyEvent(discipline_name="X", end_at=FIM_MS)

        deadline = Deadline.from_study_event(event)

        assert (deadline.type, deadline.title) == ("", "X")


class TestGradeModel:
    def test_parse(self) -> None:
        grade = Grade(discipline_name="X", type="mapa", value=8.5, weight=0.4)

        assert (grade.value, grade.weight) == (8.5, 0.4)


class TestMsToDatetime:
    def test_converte_para_horario_de_brasilia(self) -> None:
        result = ms_to_datetime(INICIO_MS)

        assert result == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert result.tzinfo is SAO_PAULO
        assert result.utcoffset() == timedelta(hours=-3)

    def test_preserva_milissegundos(self) -> None:
        assert ms_to_datetime(INICIO_MS + 841).microsecond == 841000

    def test_epoch(self) -> None:
        assert ms_to_datetime(0) == datetime(1969, 12, 31, 21, 0, tzinfo=SAO_PAULO)

    def test_none_e_datetime_passam_direto(self) -> None:
        agora = datetime(2026, 1, 1, 12, 0)

        assert ms_to_datetime(None) is None
        assert ms_to_datetime(agora) is agora

    @pytest.mark.parametrize("valor", ["1772456400000", True, 10**20])
    def test_valor_invalido(self, valor: object) -> None:
        with pytest.raises(ValueError):
            ms_to_datetime(valor)  # type: ignore[arg-type]


class TestCalculateAverage:
    def test_media_ponderada(self) -> None:
        grades = [
            Grade(discipline_name="X", type="mapa", value=8.0, weight=0.4),
            Grade(discipline_name="X", type="prova", value=6.0, weight=0.6),
        ]

        assert calculate_average(grades) == 6.8

    def test_media_simples_quando_falta_peso(self) -> None:
        grades = [
            Grade(discipline_name="X", type="mapa", value=8.0, weight=0.4),
            Grade(discipline_name="X", type="prova", value=6.0),
        ]

        assert calculate_average(grades) == 7.0

    def test_ignora_notas_sem_valor(self) -> None:
        grades = [
            Grade(discipline_name="X", type="mapa", value=8.0),
            Grade(discipline_name="X", type="prova", value=None),
        ]

        assert calculate_average(grades) == 8.0

    def test_sem_notas(self) -> None:
        assert calculate_average([]) is None

    def test_pesos_zerados(self) -> None:
        assert calculate_average([Grade(discipline_name="X", value=8.0, weight=0)]) is None
