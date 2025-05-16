"""Volvo Cars Auth API."""

from abc import ABC, abstractmethod
from asyncio import Lock
import base64
import hashlib
import logging
import secrets
import time
from typing import Any, cast

from aiohttp import ClientError, ClientSession, ClientTimeout, hdrs
from yarl import URL

from .models import TokenResponse, VolvoApiException, VolvoAuthException
from .util import redact_data

AUTHORIZE_URL = "https://volvoid.eu.volvocars.com/as/authorization.oauth2"
TOKEN_URL = "https://volvoid.eu.volvocars.com/as/token.oauth2"

_LOGGER = logging.getLogger(__name__)

_API_REQUEST_TIMEOUT = ClientTimeout(total=30)
_CLOCK_OUT_OF_SYNC_MAX_SEC = 20
_DATA_TO_REDACT = [
    "access_token",
    "code",
    "id",
    "id_token",
    "href",
    "refresh_token",
    "target",
    "username",
]


def _generate_code_verifier(code_verifier_length: int = 128) -> str:
    if not 43 <= code_verifier_length <= 128:
        msg = (
            "Parameter `code_verifier_length` must validate"
            "`43 <= code_verifier_length <= 128`."
        )
        raise ValueError(msg)
    return secrets.token_urlsafe(96)[:code_verifier_length]


def _compute_code_challenge(code_verifier: str) -> str:
    if not 43 <= len(code_verifier) <= 128:
        msg = (
            "Parameter `code_verifier` must validate `43 <= len(code_verifier) <= 128`."
        )
        raise ValueError(msg)

    hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
    encoded = base64.urlsafe_b64encode(hashed)
    return encoded.decode("ascii").replace("=", "")


class AccessTokenManager(ABC):
    """Access Token manager."""

    def __init__(self, websession: ClientSession) -> None:
        """Initialize the auth."""
        self.websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""


class VolvoCarsAuth(AccessTokenManager):
    """Volvo Cars authentication."""

    def __init__(
        self,
        websession: ClientSession,
        *,
        client_id: str,
        client_secret: str,
        scopes: list[str],
        redirect_uri: str,
        code_verifier_length: int = 128,
    ) -> None:
        """Initialize the auth."""
        super().__init__(websession)

        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._redirect_uri = redirect_uri

        self._code_verifier = _generate_code_verifier(code_verifier_length)

        credentials = f"{self._client_id}:{self._client_secret}"
        self._encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        self._token: TokenResponse
        self._token_lock = Lock()

    @property
    def token(self) -> TokenResponse | None:
        """Get current token."""
        return self._token

    @property
    def valid_token(self) -> bool:
        """Return if token is still valid."""
        return (
            self._token.expires_at > time.time() + _CLOCK_OUT_OF_SYNC_MAX_SEC
            if self._token
            else False
        )

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refresh if needed."""
        await self.async_ensure_token_valid()
        return self._token.access_token

    async def async_ensure_token_valid(self) -> None:
        """Ensure that the current token is valid."""
        async with self._token_lock:
            if self.valid_token:
                return

            if not self._token:
                raise ValueError("No token available.")

            await self.async_refresh_token(self._token.refresh_token)

    def get_auth_uri(self, state: str | None = None) -> str:
        """Get the full authorization URL."""
        query = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(self._scopes),
            "code_challenge": _compute_code_challenge(self._code_verifier),
            "code_challenge_method": "S256",
        }

        if state:
            query |= {"state": state}

        return str(URL(AUTHORIZE_URL).with_query(query))

    async def async_request_token(self, code: str) -> TokenResponse:
        """Request access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "code_verifier": self._code_verifier,
        }

        response = await self._async_request(
            hdrs.METH_POST,
            TOKEN_URL,
            headers={"Authorization": f"Basic {self._encoded_credentials}"},
            data=data,
            operation="tokens",
        )

        self._token = self._create_token_response(response)
        return self._token

    async def async_refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        response = await self._async_request(
            hdrs.METH_POST,
            TOKEN_URL,
            headers={"Authorization": f"Basic {self._encoded_credentials}"},
            data=data,
            operation="token refresh",
        )

        self._token = self._create_token_response(response)
        return self._token

    def _create_token_response(self, token: dict[str, Any]) -> TokenResponse:
        token["expires_in"] = int(token["expires_in"])
        token["expires_at"] = time.time() + token["expires_in"]

        token_response = TokenResponse.from_dict(token)

        if token_response is None:
            raise ValueError("Could not create token response.")

        return token_response

    async def _async_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        operation: str = "",
    ) -> dict[str, Any]:
        _LOGGER.debug("Request [%s]", operation)

        try:
            async with self.websession.request(
                method,
                url,
                params=params,
                headers=headers,
                data=data,
                json=json,
                timeout=_API_REQUEST_TIMEOUT,
            ) as response:
                _LOGGER.debug("Request [%s] status: %s", operation, response.status)

                json = await response.json()
                data = cast(dict[str, Any], json)

                _LOGGER.debug(
                    "Request [%s] response: %s",
                    operation,
                    redact_data(data, _DATA_TO_REDACT),
                )

                response.raise_for_status()
                return data

        except ClientError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoAuthException(ex.__class__.__name__, operation) from ex
        except TimeoutError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoApiException(ex.__class__.__name__, operation) from ex
