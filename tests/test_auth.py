"""Auth tests."""

import base64
import hashlib
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientConnectionError, ClientResponseError, ClientSession, hdrs
import pytest

from volvocarsapi import auth as auth_module
from volvocarsapi.auth import (
    AUTHORIZE_URL,
    LEGACY_VOLVOID_SERVER,
    TOKEN_URL,
    VOLVOID_SERVER,
    VolvoCarsAuth,
    VolvoIdServer,
    get_volvoid_server,
    is_legacy_client,
)
from volvocarsapi.models import VolvoApiException, VolvoAuthException
from volvocarsapi.scopes import (
    ALL_SCOPES,
    CONVE_SCOPES,
    DEFAULT_SCOPES,
    ENERGY_DEVICE_SCOPES,
    ENERGY_SCOPES,
    OPENID_SCOPES,
    RestrictedScope,
)

LEGACY_CLIENT_ID = "dc-abcdef"
CLIENT_ID = "vid-dc-abcdef"
CLIENT_SECRET = "client_secret"
REDIRECT_URI = "https://example.com/callback"

SERVER_CASES = [
    pytest.param(LEGACY_CLIENT_ID, LEGACY_VOLVOID_SERVER, id="legacy"),
    pytest.param(CLIENT_ID, VOLVOID_SERVER, id="new"),
]


@pytest.fixture(autouse=True)
def reset_legacy_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the one-time legacy client warning."""
    monkeypatch.setattr(auth_module, "_legacy_warning_logged", False)


def _create_auth(
    mock_client_session: ClientSession,
    client_id: str = "client_id",
    scopes: list[str] | None = None,
) -> VolvoCarsAuth:
    return VolvoCarsAuth(
        mock_client_session,
        client_id=client_id,
        client_secret=CLIENT_SECRET,
        scopes=scopes or ["openid"],
        redirect_uri=REDIRECT_URI,
    )


def _token_json(**overrides: Any) -> dict[str, Any]:
    return {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "token_type": "Bearer",
        "expires_in": 300,
        "id_token": "id_token",
        # Keycloak specific fields
        "refresh_expires_in": 0,
        "not-before-policy": 0,
        "session_state": "session_state",
        "scope": "openid",
    } | overrides


def _mock_token_response(
    mock_client_session: ClientSession, *responses: dict[str, Any]
) -> None:
    def _create_response(json: dict[str, Any]) -> AsyncMock:
        response = MagicMock()
        response.json = AsyncMock(return_value=json)
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = response
        return mock_response

    mock_client_session.request.side_effect = [_create_response(r) for r in responses]


def _expected_basic_auth(client_id: str) -> str:
    credentials = f"{client_id}:{CLIENT_SECRET}".encode()
    return f"Basic {base64.b64encode(credentials).decode()}"


@pytest.mark.parametrize(
    ("client_id", "expected"),
    [
        (LEGACY_CLIENT_ID, True),
        (CLIENT_ID, False),
        ("some-other-client", False),
        ("", False),
    ],
)
def test_is_legacy_client(client_id: str, expected: bool) -> None:  # noqa: FBT001
    """Test legacy client detection."""
    assert is_legacy_client(client_id) is expected


@pytest.mark.parametrize(("client_id", "expected"), SERVER_CASES)
def test_get_volvoid_server(client_id: str, expected: VolvoIdServer) -> None:
    """Test server selection by client ID."""
    assert get_volvoid_server(client_id) is expected


def test_unknown_client_prefix_uses_new_server() -> None:
    """Test client IDs without a known prefix use the new server."""
    assert get_volvoid_server("some-other-client") is VOLVOID_SERVER


def test_servers() -> None:
    """Test server configuration."""
    assert not VOLVOID_SERVER.legacy
    assert VOLVOID_SERVER.authorize_url.startswith("https://auth.volvocars.com/")
    assert VOLVOID_SERVER.token_url.startswith("https://auth.volvocars.com/")

    assert LEGACY_VOLVOID_SERVER.legacy
    assert LEGACY_VOLVOID_SERVER.authorize_url.startswith(
        "https://volvoid.eu.volvocars.com/"
    )
    assert LEGACY_VOLVOID_SERVER.token_url.startswith(
        "https://volvoid.eu.volvocars.com/"
    )


def test_deprecated_constants_point_to_legacy_server() -> None:
    """Test deprecated constants are unchanged during the transition."""
    assert LEGACY_VOLVOID_SERVER.authorize_url == AUTHORIZE_URL
    assert LEGACY_VOLVOID_SERVER.token_url == TOKEN_URL
    assert LEGACY_VOLVOID_SERVER.default_scopes == tuple(DEFAULT_SCOPES)
    assert LEGACY_VOLVOID_SERVER.all_scopes == tuple(ALL_SCOPES)


def test_scopes() -> None:
    """Test new and legacy scope sets."""
    new_default_scopes = VOLVOID_SERVER.default_scopes
    new_all_scopes = VOLVOID_SERVER.all_scopes
    wallbox_scopes = {RestrictedScope.WALLBOX_WRITE, RestrictedScope.WALLBOX_CONTROL}

    assert wallbox_scopes <= set(new_all_scopes)
    assert wallbox_scopes.isdisjoint(new_default_scopes)
    assert wallbox_scopes.isdisjoint(ALL_SCOPES)

    assert set(DEFAULT_SCOPES) <= set(new_default_scopes)
    assert set(ALL_SCOPES) <= set(new_all_scopes)
    assert set(DEFAULT_SCOPES) <= set(ALL_SCOPES)

    for scopes in (
        new_default_scopes,
        new_all_scopes,
        DEFAULT_SCOPES,
        ALL_SCOPES,
    ):
        assert len(scopes) == len(set(scopes))
        assert "offline_access" not in scopes


def test_scopes_are_backwards_compatible() -> None:
    """Test the existing scope constants keep their legacy values."""
    assert DEFAULT_SCOPES == [
        "openid",
        "conve:battery_charge_level",
        "conve:brake_status",
        "conve:climatization_start_stop",
        "conve:command_accessibility",
        "conve:commands",
        "conve:diagnostics_engine_status",
        "conve:diagnostics_workshop",
        "conve:doors_status",
        "conve:engine_status",
        "conve:fuel_status",
        "conve:lock_status",
        "conve:odometer_status",
        "conve:trip_statistics",
        "conve:tyre_status",
        "conve:vehicle_relation",
        "conve:warnings",
        "conve:windows_status",
        "energy:capability:read",
        "energy:state:read",
    ]
    assert [
        *DEFAULT_SCOPES,
        "conve:lock",
        "conve:unlock",
        "conve:engine_start_stop",
        "conve:honk_flash",
        "location:read",
    ] == ALL_SCOPES


def test_scopes_by_type() -> None:
    """Test each scope belongs to exactly one type list or is restricted."""
    groups = [
        OPENID_SCOPES,
        CONVE_SCOPES,
        ENERGY_SCOPES,
        ENERGY_DEVICE_SCOPES,
        [s.value for s in RestrictedScope],
    ]
    grouped = [scope for group in groups for scope in group]

    assert sorted(grouped) == sorted(VOLVOID_SERVER.all_scopes)
    assert VOLVOID_SERVER.default_scopes == (
        *OPENID_SCOPES,
        *CONVE_SCOPES,
        *ENERGY_SCOPES,
        *ENERGY_DEVICE_SCOPES,
    )
    assert VOLVOID_SERVER.all_scopes == (
        *VOLVOID_SERVER.default_scopes,
        *(s.value for s in RestrictedScope),
    )

    for prefix, scopes in (
        ("conve:", CONVE_SCOPES),
        ("energy:", ENERGY_SCOPES),
        ("energy_device:", ENERGY_DEVICE_SCOPES),
    ):
        assert all(scope.startswith(prefix) for scope in scopes)


@pytest.mark.parametrize(("client_id", "expected"), SERVER_CASES)
def test_auth_uses_server_for_client(
    mock_client_session: ClientSession, client_id: str, expected: VolvoIdServer
) -> None:
    """Test the auth exposes the server matching its client ID."""
    assert _create_auth(mock_client_session, client_id).server is expected


@pytest.mark.parametrize(("client_id", "expected"), SERVER_CASES)
def test_get_auth_uri(
    mock_client_session: ClientSession, client_id: str, expected: VolvoIdServer
) -> None:
    """Test the authorization URL."""
    scopes = ["openid", "conve:odometer_status"]
    auth = _create_auth(mock_client_session, client_id, scopes)

    uri = urlparse(auth.get_auth_uri("my_state"))
    query = {key: value[0] for key, value in parse_qs(uri.query).items()}

    assert f"{uri.scheme}://{uri.netloc}{uri.path}" == expected.authorize_url
    assert query == {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid conve:odometer_status",
        "code_challenge": query["code_challenge"],
        "code_challenge_method": "S256",
        "state": "my_state",
    }


def test_get_auth_uri_without_state(mock_client_session: ClientSession) -> None:
    """Test the authorization URL without state."""
    auth = _create_auth(mock_client_session, CLIENT_ID)

    query = parse_qs(urlparse(auth.get_auth_uri()).query)

    assert "state" not in query


@pytest.mark.parametrize(("client_id", "expected"), SERVER_CASES)
async def test_request_token(
    mock_client_session: ClientSession, client_id: str, expected: VolvoIdServer
) -> None:
    """Test the authorization code exchange."""
    _mock_token_response(mock_client_session, _token_json())
    auth = _create_auth(mock_client_session, client_id)
    code_challenge = parse_qs(urlparse(auth.get_auth_uri()).query)["code_challenge"][0]

    token = await auth.async_request_token("auth_code")

    call = mock_client_session.request.call_args
    assert call.args == (hdrs.METH_POST, expected.token_url)
    assert call.kwargs["headers"] == {"Authorization": _expected_basic_auth(client_id)}

    data = call.kwargs["data"]
    assert data["grant_type"] == "authorization_code"
    assert data["code"] == "auth_code"
    assert data["redirect_uri"] == REDIRECT_URI

    digest = hashlib.sha256(data["code_verifier"].encode("ascii")).digest()
    assert base64.urlsafe_b64encode(digest).decode().rstrip("=") == code_challenge

    assert token is auth.token
    assert token.access_token == "access_token"
    assert token.refresh_token == "refresh_token"
    assert token.id_token == "id_token"
    assert auth.valid_token


async def test_request_token_keeps_extra_fields(
    mock_client_session: ClientSession,
) -> None:
    """Test Keycloak specific token fields are kept as extra data."""
    _mock_token_response(mock_client_session, _token_json(expires_in="300"))
    auth = _create_auth(mock_client_session, CLIENT_ID)

    token = await auth.async_request_token("auth_code")

    assert token.expires_in == 300
    assert set(token.extra_data) == {
        "refresh_expires_in",
        "not-before-policy",
        "session_state",
        "scope",
    }


@pytest.mark.parametrize(("client_id", "expected"), SERVER_CASES)
async def test_refresh_token(
    mock_client_session: ClientSession, client_id: str, expected: VolvoIdServer
) -> None:
    """Test token refresh with a rotated refresh token."""
    _mock_token_response(
        mock_client_session,
        _token_json(access_token="new_access", refresh_token="new_refresh"),
    )
    auth = _create_auth(mock_client_session, client_id)

    token = await auth.async_refresh_token("old_refresh")

    call = mock_client_session.request.call_args
    assert call.args == (hdrs.METH_POST, expected.token_url)
    assert call.kwargs["headers"] == {"Authorization": _expected_basic_auth(client_id)}
    assert call.kwargs["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": "old_refresh",
    }
    assert token.access_token == "new_access"
    assert token.refresh_token == "new_refresh"


async def test_refresh_token_without_rotation(
    mock_client_session: ClientSession,
) -> None:
    """Test the current refresh token is kept if the server doesn't rotate it."""
    response = _token_json(access_token="new_access")
    del response["refresh_token"]
    _mock_token_response(mock_client_session, response)
    auth = _create_auth(mock_client_session, CLIENT_ID)

    token = await auth.async_refresh_token("old_refresh")

    assert token.access_token == "new_access"
    assert token.refresh_token == "old_refresh"


async def test_no_token_before_login(mock_client_session: ClientSession) -> None:
    """Test token state before the authorization code exchange."""
    auth = _create_auth(mock_client_session, CLIENT_ID)

    assert auth.token is None
    assert not auth.valid_token

    with pytest.raises(ValueError, match="No token available"):
        await auth.async_ensure_token_valid()

    with pytest.raises(ValueError, match="No token available"):
        await auth.async_get_access_token()

    mock_client_session.request.assert_not_called()


async def test_get_access_token_refreshes_expired_token(
    mock_client_session: ClientSession,
) -> None:
    """Test an expired token is refreshed."""
    _mock_token_response(
        mock_client_session,
        _token_json(expires_in=0),
        _token_json(access_token="new_access", refresh_token="new_refresh"),
    )
    auth = _create_auth(mock_client_session, CLIENT_ID)
    await auth.async_request_token("auth_code")
    assert not auth.valid_token

    assert await auth.async_get_access_token() == "new_access"

    call = mock_client_session.request.call_args
    assert call.args == (hdrs.METH_POST, VOLVOID_SERVER.token_url)
    assert call.kwargs["data"]["refresh_token"] == "refresh_token"
    assert auth.valid_token


async def test_get_access_token_uses_valid_token(
    mock_client_session: ClientSession,
) -> None:
    """Test a valid token is not refreshed."""
    _mock_token_response(mock_client_session, _token_json())
    auth = _create_auth(mock_client_session, CLIENT_ID)
    await auth.async_request_token("auth_code")

    assert await auth.async_get_access_token() == "access_token"
    assert mock_client_session.request.call_count == 1


def test_legacy_client_warns_once(
    mock_client_session: ClientSession, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a legacy client logs a migration warning once."""
    with caplog.at_level(logging.WARNING, logger=auth_module.__name__):
        _create_auth(mock_client_session, LEGACY_CLIENT_ID)
        _create_auth(mock_client_session, LEGACY_CLIENT_ID)

    warnings = [r for r in caplog.records if "legacy Volvo ID" in r.getMessage()]
    assert len(warnings) == 1
    assert "2027-01-31" in warnings[0].getMessage()


def test_new_client_does_not_warn(
    mock_client_session: ClientSession, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a new client doesn't log a migration warning."""
    with caplog.at_level(logging.WARNING, logger=auth_module.__name__):
        _create_auth(mock_client_session, CLIENT_ID)

    assert not caplog.records


async def test_token_response_is_redacted_in_logs(
    mock_client_session: ClientSession, caplog: pytest.LogCaptureFixture
) -> None:
    """Test sensitive token fields are redacted in debug logs."""
    _mock_token_response(mock_client_session, _token_json())
    auth = _create_auth(mock_client_session, CLIENT_ID)

    with caplog.at_level(logging.DEBUG, logger=auth_module.__name__):
        await auth.async_request_token("auth_code")

    for secret in ("access_token", "refresh_token", "id_token", "session_state"):
        assert f"'{secret}'" in caplog.text
        assert f"': '{secret}'" not in caplog.text


async def test_refresh_token_response_error_exposes_status(
    mock_client_session: ClientSession,
) -> None:
    """Test HTTP status is exposed when the token request fails."""
    mock_client_session.request.side_effect = ClientResponseError(
        None, None, status=400
    )

    with pytest.raises(VolvoAuthException) as exc_info:
        await _create_auth(mock_client_session).async_refresh_token("refresh")

    assert exc_info.value.status == 400


async def test_refresh_token_connection_error_has_no_status(
    mock_client_session: ClientSession,
) -> None:
    """Test status is `None` when the token request fails without a response."""
    mock_client_session.request.side_effect = ClientConnectionError()

    with pytest.raises(VolvoAuthException) as exc_info:
        await _create_auth(mock_client_session).async_refresh_token("refresh")

    assert exc_info.value.status is None


async def test_refresh_token_timeout_has_no_status(
    mock_client_session: ClientSession,
) -> None:
    """Test status is `None` when the token request times out."""
    mock_client_session.request.side_effect = TimeoutError()

    with pytest.raises(VolvoApiException) as exc_info:
        await _create_auth(mock_client_session).async_refresh_token("refresh")

    assert not isinstance(exc_info.value, VolvoAuthException)
    assert exc_info.value.status is None
