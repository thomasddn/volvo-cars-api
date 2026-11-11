"""Volvo Cars Auth API."""

from abc import ABC, abstractmethod
from asyncio import Lock
import base64
from dataclasses import dataclass
from datetime import date
import hashlib
import logging
import secrets
import time
from typing import Any, cast

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout, hdrs
from yarl import URL

from .models import TokenResponse, VolvoApiException, VolvoAuthException
from .scopes import ALL_SCOPES, DEFAULT_SCOPES, LEGACY_ALL_SCOPES, LEGACY_DEFAULT_SCOPES
from .util import redact_data


@dataclass(frozen=True, slots=True)
class VolvoIdServer:
    """Volvo ID authorization server."""

    authorize_url: str
    token_url: str
    default_scopes: tuple[str, ...]
    all_scopes: tuple[str, ...]
    legacy: bool = False


VOLVOID_SERVER = VolvoIdServer(
    authorize_url="https://auth.volvocars.com/realms/volvocars/protocol/openid-connect/auth",
    token_url="https://auth.volvocars.com/realms/volvocars/protocol/openid-connect/token",
    default_scopes=tuple(DEFAULT_SCOPES),
    all_scopes=tuple(ALL_SCOPES),
)

LEGACY_VOLVOID_SERVER = VolvoIdServer(
    authorize_url="https://volvoid.eu.volvocars.com/as/authorization.oauth2",
    token_url="https://volvoid.eu.volvocars.com/as/token.oauth2",
    default_scopes=tuple(LEGACY_DEFAULT_SCOPES),
    all_scopes=tuple(LEGACY_ALL_SCOPES),
    legacy=True,
)

LEGACY_CLIENT_ID_PREFIX = "dc-"
VOLVOID_MIGRATION_DEADLINE = date(2027, 1, 31)
VOLVOID_MIGRATION_URL = "https://developer.volvocars.com/news/volvoid-migration/"

# Deprecated: use `get_volvoid_server(client_id)` instead. These keep pointing to the
# legacy Volvo ID system until the migration deadline has passed.
AUTHORIZE_URL = LEGACY_VOLVOID_SERVER.authorize_url
TOKEN_URL = LEGACY_VOLVOID_SERVER.token_url

_LOGGER = logging.getLogger(__name__)

_API_REQUEST_TIMEOUT = ClientTimeout(total=30)
_CLOCK_OUT_OF_SYNC_MAX_SEC = 20
_DATA_TO_REDACT = [
    "access_token",
    "code",
    "email",
    "family_name",
    "given_name",
    "id",
    "id_token",
    "href",
    "name",
    "preferred_username",
    "refresh_token",
    "session_state",
    "sid",
    "target",
    "username",
]

_legacy_warning_logged = False


def is_legacy_client(client_id: str) -> bool:
    """Return if the client ID belongs to the legacy Volvo ID system."""
    return client_id.startswith(LEGACY_CLIENT_ID_PREFIX)


def get_volvoid_server(client_id: str) -> VolvoIdServer:
    """Return the Volvo ID authorization server for the given client ID."""
    return LEGACY_VOLVOID_SERVER if is_legacy_client(client_id) else VOLVOID_SERVER


def _warn_legacy_client() -> None:
    global _legacy_warning_logged  # noqa: PLW0603

    if _legacy_warning_logged:
        return

    _legacy_warning_logged = True
    _LOGGER.warning(
        "Your Volvo API application uses the legacy Volvo ID system, which stops "
        "working after %s. Create a new application to migrate. See %s",
        VOLVOID_MIGRATION_DEADLINE.isoformat(),
        VOLVOID_MIGRATION_URL,
    )


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
        self._server = get_volvoid_server(client_id)

        if self._server.legacy:
            _warn_legacy_client()

        self._code_verifier = _generate_code_verifier(code_verifier_length)

        credentials = f"{self._client_id}:{self._client_secret}"
        self._encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        self._token: TokenResponse | None = None
        self._token_lock = Lock()

    @property
    def server(self) -> VolvoIdServer:
        """Get the Volvo ID authorization server used by this client."""
        return self._server

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
        return cast("TokenResponse", self._token).access_token

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

        return str(URL(self._server.authorize_url).with_query(query))

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
            self._server.token_url,
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
            self._server.token_url,
            headers={"Authorization": f"Basic {self._encoded_credentials}"},
            data=data,
            operation="token refresh",
        )

        # Keep the current refresh token if the server doesn't rotate it.
        response.setdefault("refresh_token", refresh_token)

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
                data = cast("dict[str, Any]", json)

                _LOGGER.debug(
                    "Request [%s] response: %s",
                    operation,
                    redact_data(data, _DATA_TO_REDACT),
                )

                response.raise_for_status()
                return data

        except ClientError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            status = ex.status if isinstance(ex, ClientResponseError) else None
            raise VolvoAuthException(
                ex.__class__.__name__, operation, status=status
            ) from ex
        except TimeoutError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoApiException(ex.__class__.__name__, operation) from ex
