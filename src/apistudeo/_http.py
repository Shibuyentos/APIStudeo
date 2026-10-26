"""Transporte HTTP: httpx.Client, headers, rate limit e renovação do token em 401."""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import httpx

from apistudeo import endpoints
from apistudeo.exceptions import AuthenticationError, RateLimitError, StudeoAPIError, StudeoError
from apistudeo.utils import mask_token

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    ),
    "Origin": "https://studeo.unicesumar.edu.br",
}


class HttpTransport:
    """Envia os requests para a API do Studeo e guarda o token da sessão."""

    def __init__(self, *, base_url: str, timeout: float, min_request_interval: float) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        )
        self._min_request_interval = min_request_interval
        self._last_request_at = -math.inf
        self.token: str | None = None
        self.refresh_token: str | None = None

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    def set_tokens(self, token: str, refresh_token: str | None = None) -> None:
        """Define os tokens da sessão. O token vai no header Authorization, sem prefixo Bearer."""
        self.token = token
        self.refresh_token = refresh_token
        self._client.headers["Authorization"] = token
        logger.debug("Token configurado: %s", mask_token(token))

    def clear_tokens(self) -> None:
        self.token = None
        self.refresh_token = None
        self._client.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        retry_on_401: bool = True,
    ) -> httpx.Response:
        """Faz o request e converte erros HTTP em exceções da lib.

        Em 401, se houver refresh token, renova o token e repete o request uma vez.
        """
        response = self._send(method, path, params=params, json=json)
        if response.status_code == 401 and retry_on_401 and self.refresh_token:
            logger.warning("401 em %s %s; renovando o token e repetindo.", method, path)
            self.renew()
            response = self._send(method, path, params=params, json=json)
        _raise_for_status(response, method, path)
        return response

    def renew(self) -> tuple[str, str | None]:
        """Troca o refresh token por um token novo e devolve (token, refresh_token)."""
        if not self.refresh_token:
            raise AuthenticationError("Não há refresh token para renovar a sessão.")
        response = self._send(
            "POST", endpoints.AUTH_TOKEN_RENEW, json={"refreshToken": self.refresh_token}
        )
        data = _json_or_none(response) if response.is_success else None
        if not isinstance(data, dict):
            data = {}
        token = data.get("token") or data.get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthenticationError(
                f"Não foi possível renovar o token (status {response.status_code})."
            )
        refresh_token = data.get("refreshToken")
        if not isinstance(refresh_token, str) or not refresh_token:
            refresh_token = self.refresh_token
        self.set_tokens(token, refresh_token)
        logger.info("Token renovado.")
        return token, refresh_token

    def close(self) -> None:
        self._client.close()

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        self._wait_rate_limit()
        logger.debug("%s %s", method, path)
        try:
            response = self._client.request(method, path, params=params, json=json)
        except httpx.RequestError as exc:
            raise StudeoError(f"Falha de conexão em {method} {path}: {exc}") from exc
        logger.debug("%s %s -> %d", method, path, response.status_code)
        return response

    def _wait_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_request_interval:
            wait = self._min_request_interval - elapsed
            logger.debug("Rate limit: aguardando %.1fs", wait)
            time.sleep(wait)
        self._last_request_at = time.monotonic()


def _raise_for_status(response: httpx.Response, method: str, path: str) -> None:
    status = response.status_code
    if status < 400:
        return
    if status == 401:
        raise AuthenticationError(
            f"Não autorizado (401) em {method} {path}: token ausente, expirado ou inválido."
        )
    error_class = RateLimitError if status == 429 else StudeoAPIError
    raise error_class(
        f"Erro {status} em {method} {path}.", status_code=status, response_text=response.text
    )


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
