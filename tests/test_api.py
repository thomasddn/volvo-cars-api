"""API tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from aiohttp import ClientResponseError, ClientSession, RequestInfo
import pytest

from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.auth import VolvoCarsAuth
from volvocarsapi.models import VolvoApiException, VolvoAuthException

from . import configure_mock, load_json_fixture


async def test_get_odometer_successful(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test successful odometer request."""
    odometer_json = load_json_fixture("odometer")
    _mock_response(mock_client_session, odometer_json)

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    result = await api.async_get_odometer()
    assert result["odometer"].value == 30000
    assert result["odometer"].unit == "km"
    assert result["odometer"].timestamp == datetime(
        2024, 12, 30, 14, 18, 56, 0, tzinfo=UTC
    )


async def test_get_odometer_token_failure(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test token failure for odometer request."""
    configure_mock(
        mock_token_manager.async_get_access_token,
        side_effect=ClientResponseError(None, None, status=400),
    )

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoAuthException):
        await api.async_get_odometer()


async def test_get_odometer_failure(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test general failure for odometer request."""
    _mock_response_failure(mock_client_session, 500)

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException):
        await api.async_get_odometer()


async def test_get_odometer_auth_failure(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test auth failure for odometer request."""
    _mock_response_failure(mock_client_session, 401)

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoAuthException):
        await api.async_get_odometer()


async def test_access_token_successful(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test successful access token request."""
    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    access_token = await api.async_get_access_token()
    assert access_token == "valid_token_123"


@pytest.mark.parametrize(
    "status",
    [400, 401, 403],
)
async def test_access_token_raises_auth_exception(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth, status: int
) -> None:
    """Test if getting access token raises a `VolvoAuthException`."""
    configure_mock(
        mock_token_manager.async_get_access_token,
        side_effect=ClientResponseError(None, None, status=status),
    )

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoAuthException):
        await api.async_get_access_token()


@pytest.mark.parametrize(
    "status",
    [404, 500],
)
async def test_access_token_raises_api_exception(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth, status: int
) -> None:
    """Test if getting access token raises a `VolvoApiException`."""
    configure_mock(
        mock_token_manager.async_get_access_token,
        side_effect=ClientResponseError(None, None, status=status),
    )

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException):
        await api.async_get_access_token()


def _mock_response(mock_client_session: ClientSession, json: dict) -> None:
    mock_response = AsyncMock()
    mock_response.__aenter__.return_value.json = AsyncMock(return_value=json)
    mock_client_session.request.return_value = mock_response


def _mock_response_failure(mock_client_session: ClientSession, status: int) -> None:
    mock_client_session.request.side_effect = ClientResponseError(
        RequestInfo(url="http://127.0.0.1", method="GET", headers={}),
        None,
        status=status,
    )
