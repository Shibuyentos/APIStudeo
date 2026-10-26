"""Cliente público da APIStudeo."""

from __future__ import annotations

import logging
import re
from types import TracebackType

import httpx

from apistudeo import endpoints
from apistudeo._http import HttpTransport
from apistudeo.exceptions import AuthenticationError, StudeoAPIError
from apistudeo.models import AuthInfo
from apistudeo.utils import mask_cpf, mask_token

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
DEFAULT_MIN_REQUEST_INTERVAL = 2.0

_JWT_PATTERN = re.compile(r"(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)")
_TOKEN_COOKIES = ("token", "auth_token", "JSESSIONID")


class StudeoClient:
    """Cliente da API do Studeo.

    Exemplo::

        with StudeoClient(cpf="00000000000", senha="...") as studeo:
            print(studeo.get_user_info().name)
    """

    def __init__(
        self,
        cpf: str | None = None,
        senha: str | None = None,
        *,
        base_url: str = endpoints.BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> None:
        """Cria o cliente. O login acontece no primeiro request que precisar de token.

        Args:
            cpf: CPF do aluno, sem formatação (enviado como ``username`` no login).
            senha: Senha do Studeo.
            base_url: URL base da API.
            timeout: Timeout de cada request, em segundos.
            min_request_interval: Intervalo mínimo entre requests, em segundos.
        """
        if bool(cpf) != bool(senha):
            raise ValueError("Informe cpf e senha juntos, ou use StudeoClient.from_token().")
        if min_request_interval < 0:
            raise ValueError("min_request_interval não pode ser negativo.")
        self._cpf = cpf or None
        self._senha = senha or None
        self._http = HttpTransport(
            base_url=base_url, timeout=timeout, min_request_interval=min_request_interval
        )

    @classmethod
    def from_token(
        cls,
        token: str,
        refresh_token: str | None = None,
        *,
        base_url: str = endpoints.BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
    ) -> StudeoClient:
        """Cria um cliente a partir de um token já obtido, sem CPF e senha."""
        if not token:
            raise ValueError("token não pode ser vazio.")
        client = cls(base_url=base_url, timeout=timeout, min_request_interval=min_request_interval)
        client._http.set_tokens(token, refresh_token)
        return client

    def login(self) -> AuthInfo:
        """Faz login com CPF e senha e guarda o token na sessão."""
        if not (self._cpf and self._senha):
            raise AuthenticationError(
                "Login exige cpf e senha. Para usar um token existente, use "
                "StudeoClient.from_token()."
            )
        logger.info("Fazendo login no Studeo (CPF %s)", mask_cpf(self._cpf))
        try:
            response = self._http.request(
                "POST",
                endpoints.AUTH_TOKEN_CREATE,
                json={"username": self._cpf, "password": self._senha},
                retry_on_401=False,
            )
        except AuthenticationError as exc:
            raise AuthenticationError("Login recusado (401): confira CPF e senha.") from exc
        except StudeoAPIError as exc:
            if exc.status_code in (400, 403):
                raise AuthenticationError(
                    f"Login recusado ({exc.status_code}): confira CPF e senha."
                ) from exc
            raise

        token, refresh_token = _extract_tokens(response)
        if not token:
            raise AuthenticationError(
                f"Token não encontrado na resposta do login (status {response.status_code})."
            )
        self._http.set_tokens(token, refresh_token)
        logger.info("Login concluído (token %s)", mask_token(token))
        return AuthInfo(token=token, refresh_token=refresh_token)

    def renew_token(self) -> AuthInfo:
        """Renova o token da sessão usando o refresh token."""
        token, refresh_token = self._http.renew()
        return AuthInfo(token=token, refresh_token=refresh_token)

    def logout(self) -> None:
        """Revoga o token atual no Studeo e limpa a sessão local, mesmo se a API falhar."""
        token = self._http.token
        if not token:
            return
        payload = {"token": token}
        if self._http.refresh_token:
            payload["refreshToken"] = self._http.refresh_token
        try:
            self._http.request(
                "POST", endpoints.AUTH_TOKEN_REVOKE, json=payload, retry_on_401=False
            )
        finally:
            self._http.clear_tokens()
        logger.info("Logout concluído.")

    def close(self) -> None:
        """Fecha a conexão HTTP. Não faz logout."""
        self._http.close()

    def __enter__(self) -> StudeoClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def _extract_tokens(response: httpx.Response) -> tuple[str | None, str | None]:
    """Procura o token do login no body JSON, no texto (regex JWT), nos headers e nos cookies."""
    token: str | None = None
    refresh_token: str | None = None

    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        token = _non_empty_str(data.get("token"))
        refresh_token = _non_empty_str(data.get("refreshToken"))

    if not token:
        matches = _JWT_PATTERN.findall(response.text)
        if matches:
            token = matches[0]
            if len(matches) > 1:
                refresh_token = matches[1]

    if not token:
        auth_header = response.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        token = response.headers.get("X-Auth-Token") or response.headers.get("Token")

    if not token:
        for cookie_name in _TOKEN_COOKIES:
            if cookie_name in response.cookies:
                token = response.cookies[cookie_name]
                break

    return token, refresh_token


def _non_empty_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
