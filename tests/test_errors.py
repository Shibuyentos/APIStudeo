"""Testes de erros: 401 com renew, status HTTP, falha de rede, formato inesperado e rate limit."""

from __future__ import annotations

import time

import httpx
import pytest
from conftest import FAKE_REFRESH, FAKE_TOKEN, api_url
from pytest_httpx import HTTPXMock

from apistudeo import (
    AuthenticationError,
    RateLimitError,
    StudeoAPIError,
    StudeoClient,
    StudeoError,
    endpoints,
)
from apistudeo.exceptions import MAX_RESPONSE_TEXT

INFO_URL = api_url(endpoints.USUARIO_INFO_LOGIN)
RENEW_URL = api_url(endpoints.AUTH_TOKEN_RENEW)
NOVO_TOKEN = "eyJ.novo.token"


class TestRenovacaoEm401:
    def test_renova_e_repete_o_request(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, user_payload: dict
    ) -> None:
        httpx_mock.add_response(
            url=INFO_URL, status_code=401, match_headers={"Authorization": FAKE_TOKEN}
        )
        httpx_mock.add_response(
            url=RENEW_URL,
            method="POST",
            match_json={"refreshToken": FAKE_REFRESH},
            json={"token": NOVO_TOKEN, "refreshToken": "eyJ.novo.refresh"},
        )
        httpx_mock.add_response(
            url=INFO_URL, match_headers={"Authorization": NOVO_TOKEN}, json=user_payload
        )

        user = studeo.get_user_info()

        assert user.name == "Aluno Teste"
        assert [r.method for r in httpx_mock.get_requests()] == ["GET", "POST", "GET"]

    @pytest.mark.parametrize("status", [401, 500])
    def test_renew_falhando_vira_authentication_error(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, status: int
    ) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=401)
        httpx_mock.add_response(url=RENEW_URL, method="POST", status_code=status)

        with pytest.raises(AuthenticationError, match="renovar"):
            studeo.get_user_info()

    def test_sem_refresh_token_nao_tenta_renovar(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=401)

        with StudeoClient.from_token(FAKE_TOKEN, min_request_interval=0) as studeo:
            with pytest.raises(AuthenticationError, match="401"):
                studeo.get_user_info()

        assert len(httpx_mock.get_requests()) == 1

    def test_401_de_novo_depois_do_renew(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=401, is_reusable=True)
        httpx_mock.add_response(url=RENEW_URL, method="POST", json={"token": NOVO_TOKEN})

        with pytest.raises(AuthenticationError, match="401"):
            studeo.get_user_info()

        assert [r.method for r in httpx_mock.get_requests()] == ["GET", "POST", "GET"]


class TestStatusHttp:
    @pytest.mark.parametrize("status", [404, 500])
    def test_vira_studeo_api_error_com_status_code(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, status: int
    ) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=status, text="erro " * 300)

        with pytest.raises(StudeoAPIError) as exc_info:
            studeo.get_user_info()

        assert exc_info.value.status_code == status
        assert not isinstance(exc_info.value, RateLimitError)
        assert len(exc_info.value.response_text) == MAX_RESPONSE_TEXT

    def test_429_vira_rate_limit_error(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=429, text="muitas requisições")

        with pytest.raises(RateLimitError) as exc_info:
            studeo.get_user_info()

        assert exc_info.value.status_code == 429
        assert exc_info.value.response_text == "muitas requisições"
        assert isinstance(exc_info.value, StudeoAPIError)


class TestRespostasInesperadas:
    def test_falha_de_conexao_vira_studeo_error(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_exception(httpx.ConnectError("sem rede"), url=INFO_URL)

        with pytest.raises(StudeoError, match="Falha de conexão") as exc_info:
            studeo.get_user_info()

        assert not isinstance(exc_info.value, StudeoAPIError)
        assert isinstance(exc_info.value.__cause__, httpx.ConnectError)

    def test_json_invalido(self, httpx_mock: HTTPXMock, studeo: StudeoClient) -> None:
        httpx_mock.add_response(url=INFO_URL, text="<html>em manutenção</html>")

        with pytest.raises(StudeoAPIError, match="formato esperado") as exc_info:
            studeo.get_user_info()

        assert exc_info.value.status_code == 200

    def test_formato_diferente_do_esperado(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        url = api_url(endpoints.DISCIPLINAS_CURRICULARES.format(curricular="true"))
        httpx_mock.add_response(url=url, json={"erro": "não é uma lista"})

        with pytest.raises(StudeoAPIError, match="formato esperado"):
            studeo.get_disciplines()

    def test_resposta_vazia_onde_se_espera_um_objeto(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=INFO_URL, status_code=204)

        with pytest.raises(StudeoAPIError, match="Resposta vazia"):
            studeo.get_user_info()


class TestRateLimit:
    def test_espera_o_intervalo_minimo_entre_requests(
        self,
        httpx_mock: HTTPXMock,
        monkeypatch: pytest.MonkeyPatch,
        time_info_payload: dict,
    ) -> None:
        esperas: list[float] = []
        monkeypatch.setattr(time, "sleep", esperas.append)
        httpx_mock.add_response(
            url=api_url(endpoints.AUTH_TOKEN_TIME_INFO), json=time_info_payload, is_reusable=True
        )

        with StudeoClient.from_token(FAKE_TOKEN, min_request_interval=5) as studeo:
            studeo.get_server_time()
            studeo.get_server_time()

        assert len(esperas) == 1
        assert 0 < esperas[0] <= 5

    def test_intervalo_negativo_e_invalido(self) -> None:
        with pytest.raises(ValueError, match="negativo"):
            StudeoClient(min_request_interval=-1)
