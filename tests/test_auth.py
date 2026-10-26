"""Testes de login, extração do token, renovação, logout e ciclo de vida do cliente."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
import pytest
from conftest import FAKE_CPF, FAKE_REFRESH, FAKE_SENHA, FAKE_TOKEN, api_url
from pydantic import ValidationError
from pytest_httpx import HTTPXMock

from apistudeo import (
    AuthenticationError,
    AuthInfo,
    ServerTime,
    StudeoAPIError,
    StudeoClient,
    User,
    endpoints,
)
from apistudeo.client import _extract_tokens
from apistudeo.utils import SAO_PAULO

LOGIN_URL = api_url(endpoints.AUTH_TOKEN_CREATE)
RENEW_URL = api_url(endpoints.AUTH_TOKEN_RENEW)
REVOKE_URL = api_url(endpoints.AUTH_TOKEN_REVOKE)

JWT_ACESSO = "eyJfake.eyJacesso.assinatura"
JWT_RENOVACAO = "eyJfake.eyJrenovacao.assinatura"


class TestLogin:
    def test_token_no_body(self, httpx_mock: HTTPXMock, studeo_login: StudeoClient) -> None:
        httpx_mock.add_response(
            url=LOGIN_URL,
            method="POST",
            match_json={"username": FAKE_CPF, "password": FAKE_SENHA},
            json={"token": FAKE_TOKEN, "refreshToken": FAKE_REFRESH},
        )
        httpx_mock.add_response(
            url=REVOKE_URL, method="POST", match_headers={"Authorization": FAKE_TOKEN}
        )

        auth = studeo_login.login()

        assert auth.token == FAKE_TOKEN
        assert auth.refresh_token == FAKE_REFRESH
        studeo_login.logout()

    @pytest.mark.parametrize(
        ("resposta", "esperado"),
        [
            ({"text": JWT_ACESSO}, (JWT_ACESSO, None)),
            ({"json": JWT_ACESSO}, (JWT_ACESSO, None)),
            ({"text": f"{JWT_ACESSO} {JWT_RENOVACAO}"}, (JWT_ACESSO, JWT_RENOVACAO)),
        ],
        ids=["texto-puro", "string-json", "dois-jwts"],
    )
    def test_token_somente_como_texto(
        self,
        httpx_mock: HTTPXMock,
        studeo_login: StudeoClient,
        resposta: dict[str, str],
        esperado: tuple[str, str | None],
    ) -> None:
        httpx_mock.add_response(url=LOGIN_URL, method="POST", **resposta)

        auth = studeo_login.login()

        assert (auth.token, auth.refresh_token) == esperado

    def test_sem_token_levanta_authentication_error(
        self, httpx_mock: HTTPXMock, studeo_login: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=LOGIN_URL, method="POST", json={"mensagem": "ok"})

        with pytest.raises(AuthenticationError, match="Token não encontrado"):
            studeo_login.login()

    @pytest.mark.parametrize("status", [400, 401, 403])
    def test_credenciais_recusadas(
        self, httpx_mock: HTTPXMock, studeo_login: StudeoClient, status: int
    ) -> None:
        httpx_mock.add_response(url=LOGIN_URL, method="POST", status_code=status)

        with pytest.raises(AuthenticationError, match=f"Login recusado \\({status}\\)"):
            studeo_login.login()

    def test_erro_do_servidor_no_login_continua_sendo_erro_de_api(
        self, httpx_mock: HTTPXMock, studeo_login: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=LOGIN_URL, method="POST", status_code=500)

        with pytest.raises(StudeoAPIError) as exc_info:
            studeo_login.login()

        assert exc_info.value.status_code == 500

    def test_login_sem_credenciais(self) -> None:
        with StudeoClient(min_request_interval=0) as studeo:
            with pytest.raises(AuthenticationError, match="exige cpf e senha"):
                studeo.login()

    @pytest.mark.parametrize("credenciais", [{"cpf": FAKE_CPF}, {"senha": FAKE_SENHA}])
    def test_construtor_exige_cpf_e_senha_juntos(self, credenciais: dict[str, str]) -> None:
        with pytest.raises(ValueError, match="cpf e senha juntos"):
            StudeoClient(**credenciais)

    def test_logs_nao_expoem_cpf_senha_nem_token(
        self,
        httpx_mock: HTTPXMock,
        studeo_login: StudeoClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        token_longo = "token-falso-" + "x" * 40
        httpx_mock.add_response(url=LOGIN_URL, method="POST", json={"token": token_longo})
        caplog.set_level(logging.DEBUG, logger="apistudeo")

        studeo_login.login()

        assert caplog.records
        assert FAKE_CPF not in caplog.text
        assert FAKE_SENHA not in caplog.text
        assert token_longo not in caplog.text
        assert "***0000" in caplog.text


class TestExtractTokens:
    @pytest.mark.parametrize(
        ("kwargs", "esperado"),
        [
            ({"json": {"token": "tok-body", "refreshToken": "ref-body"}}, ("tok-body", "ref-body")),
            ({"headers": {"Authorization": "Bearer tok-header"}}, ("tok-header", None)),
            ({"headers": {"X-Auth-Token": "tok-x-auth"}}, ("tok-x-auth", None)),
            ({"headers": {"Token": "tok-token"}}, ("tok-token", None)),
            ({"headers": {"Set-Cookie": "auth_token=tok-cookie; Path=/"}}, ("tok-cookie", None)),
            (
                {"headers": {"Set-Cookie": "JSESSIONID=sessao-falsa; Path=/"}},
                ("sessao-falsa", None),
            ),
            ({"json": {}}, (None, None)),
            ({"json": {"token": 123}}, (None, None)),
        ],
        ids=[
            "body",
            "authorization-bearer",
            "x-auth-token",
            "token-header",
            "cookie-auth-token",
            "cookie-jsessionid",
            "nenhuma-fonte",
            "token-nao-string",
        ],
    )
    def test_fontes(self, kwargs: dict, esperado: tuple[str | None, str | None]) -> None:
        response = httpx.Response(200, request=httpx.Request("POST", LOGIN_URL), **kwargs)

        assert _extract_tokens(response) == esperado

    def test_body_tem_prioridade_sobre_headers(self) -> None:
        response = httpx.Response(
            200,
            request=httpx.Request("POST", LOGIN_URL),
            json={"token": "tok-body"},
            headers={"Authorization": "Bearer tok-header"},
        )

        assert _extract_tokens(response) == ("tok-body", None)


class TestRenewToken:
    def test_renova_e_guarda_os_dois_tokens(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(
            url=RENEW_URL,
            method="POST",
            match_json={"refreshToken": FAKE_REFRESH},
            json={"token": "eyJ.novo.token", "refreshToken": "eyJ.novo.refresh"},
        )
        httpx_mock.add_response(
            url=REVOKE_URL,
            method="POST",
            match_headers={"Authorization": "eyJ.novo.token"},
            match_json={"token": "eyJ.novo.token", "refreshToken": "eyJ.novo.refresh"},
        )

        auth = studeo.renew_token()

        assert (auth.token, auth.refresh_token) == ("eyJ.novo.token", "eyJ.novo.refresh")
        studeo.logout()

    def test_mantem_refresh_antigo_se_a_api_nao_mandar_outro(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=RENEW_URL, method="POST", json={"token": "eyJ.novo.token"})

        auth = studeo.renew_token()

        assert auth.refresh_token == FAKE_REFRESH

    def test_sem_refresh_token(self) -> None:
        with StudeoClient.from_token(FAKE_TOKEN, min_request_interval=0) as studeo:
            with pytest.raises(AuthenticationError, match="refresh token"):
                studeo.renew_token()

    @pytest.mark.parametrize("resposta", [{"status_code": 401}, {"json": {"erro": "x"}}])
    def test_falha_ao_renovar(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, resposta: dict
    ) -> None:
        httpx_mock.add_response(url=RENEW_URL, method="POST", **resposta)

        with pytest.raises(AuthenticationError, match="Não foi possível renovar"):
            studeo.renew_token()


class TestLogout:
    def test_revoga_tokens_e_limpa_a_sessao(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(
            url=REVOKE_URL,
            method="POST",
            match_headers={"Authorization": FAKE_TOKEN},
            match_json={"token": FAKE_TOKEN, "refreshToken": FAKE_REFRESH},
        )

        studeo.logout()
        studeo.logout()

        assert len(httpx_mock.get_requests()) == 1

    def test_limpa_a_sessao_mesmo_se_a_api_falhar(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient
    ) -> None:
        httpx_mock.add_response(url=REVOKE_URL, method="POST", status_code=500)

        with pytest.raises(StudeoAPIError):
            studeo.logout()
        studeo.logout()

        assert len(httpx_mock.get_requests()) == 1


class TestLoginPreguicoso:
    def test_primeiro_request_faz_login_uma_vez(
        self, httpx_mock: HTTPXMock, studeo_login: StudeoClient, user_payload: dict
    ) -> None:
        httpx_mock.add_response(url=LOGIN_URL, method="POST", json={"token": FAKE_TOKEN})
        httpx_mock.add_response(
            url=api_url(endpoints.USUARIO_INFO_LOGIN),
            match_headers={"Authorization": FAKE_TOKEN},
            json=user_payload,
            is_reusable=True,
        )

        studeo_login.get_user_info()
        studeo_login.get_user_info()

        assert [r.method for r in httpx_mock.get_requests()] == ["POST", "GET", "GET"]

    def test_sem_token_nem_credenciais(self) -> None:
        with StudeoClient(min_request_interval=0) as studeo:
            with pytest.raises(AuthenticationError, match="exige cpf e senha"):
                studeo.get_user_info()


class TestUsuarioEHoraDoServidor:
    def test_get_user_info(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, user_payload: dict
    ) -> None:
        httpx_mock.add_response(
            url=api_url(endpoints.USUARIO_INFO_LOGIN),
            match_headers={"Authorization": FAKE_TOKEN},
            json=user_payload,
        )

        user = studeo.get_user_info()

        assert user.name == "Aluno Teste"
        assert user.course_name == "Curso Teste"
        assert user.raw == user_payload

    def test_get_server_time(
        self, httpx_mock: HTTPXMock, studeo: StudeoClient, time_info_payload: dict
    ) -> None:
        httpx_mock.add_response(url=api_url(endpoints.AUTH_TOKEN_TIME_INFO), json=time_info_payload)

        server_time = studeo.get_server_time()

        assert server_time.now == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert server_time.timezone_id == "America/Sao_Paulo"


class TestModels:
    def test_auth_info_nao_expoe_tokens_no_repr(self) -> None:
        auth = AuthInfo(token=FAKE_TOKEN, refresh_token=FAKE_REFRESH)

        assert FAKE_TOKEN not in repr(auth)
        assert FAKE_REFRESH not in repr(auth)

    def test_user(self, user_payload: dict) -> None:
        user = User.model_validate(user_payload)

        assert user.id == 1001
        assert user.user_code == "00000000-0"
        assert user.name == "Aluno Teste"
        assert user.email == "aluno.teste@example.com"
        assert user.cpf == FAKE_CPF
        assert user.profile == "ALUNO"
        assert user.last_access_at == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert [(c.name, c.code) for c in user.courses] == [("Curso Teste", "CURSO_TESTE")]
        assert user.course_name == "Curso Teste"
        assert user.raw == user_payload

    def test_user_nao_expoe_cpf_nem_email_no_repr(self, user_payload: dict) -> None:
        texto = repr(User.model_validate(user_payload))

        assert FAKE_CPF not in texto
        assert "aluno.teste@example.com" not in texto
        assert "Aluno Teste" in texto

    def test_user_sem_cursos(self, user_payload: dict) -> None:
        user = User.model_validate({**user_payload, "cursoList": None})

        assert user.courses == []
        assert user.course_name is None

    def test_server_time(self, time_info_payload: dict) -> None:
        server_time = ServerTime.model_validate(time_info_payload)

        assert server_time.now == datetime(2026, 3, 2, 10, 0, tzinfo=SAO_PAULO)
        assert server_time.now.tzinfo is SAO_PAULO
        assert server_time.timezone_id == "America/Sao_Paulo"
        assert server_time.offset_minutes == -180

    def test_server_time_sem_timestamp_e_invalido(self, time_info_payload: dict) -> None:
        del time_info_payload["timestamp"]

        with pytest.raises(ValidationError):
            ServerTime.model_validate(time_info_payload)


class TestCicloDeVida:
    def test_from_token_exige_token(self) -> None:
        with pytest.raises(ValueError, match="token"):
            StudeoClient.from_token("")

    def test_context_manager_fecha_o_cliente(self) -> None:
        with StudeoClient.from_token(FAKE_TOKEN, min_request_interval=0) as studeo:
            assert not studeo._http.is_closed

        assert studeo._http.is_closed
