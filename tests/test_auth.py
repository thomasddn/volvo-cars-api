"""Auth tests."""

from aiohttp import ClientConnectionError, ClientResponseError, ClientSession
import pytest

from volvocarsapi.auth import VolvoCarsAuth
from volvocarsapi.models import VolvoApiException, VolvoAuthException


def _create_auth(mock_client_session: ClientSession) -> VolvoCarsAuth:
    return VolvoCarsAuth(
        mock_client_session,
        client_id="client_id",
        client_secret="client_secret",
        scopes=["openid"],
        redirect_uri="https://example.com",
    )


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
