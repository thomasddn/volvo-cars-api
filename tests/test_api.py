"""API tests."""

from unittest.mock import AsyncMock

from aiohttp import ClientResponseError, ClientSession
import pytest

from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.auth import VolvoCarsAuth
from volvocarsapi.models import VolvoApiException, VolvoAuthException


@pytest.mark.parametrize(
    "status",
    [400, 401, 403],
)
async def test_access_token_raises_auth_exception(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth,
    status: int
) -> None:
    mock_token_manager.async_get_access_token = AsyncMock(side_effect=ClientResponseError(None, None, status=status))

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoAuthException):
        await api.async_get_access_token()


@pytest.mark.parametrize(
    "status",
    [404, 500],
)
async def test_access_token_raises_api_exception(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth,
    status: int
) -> None:
    mock_token_manager.async_get_access_token = AsyncMock(side_effect=ClientResponseError(None, None, status=status))

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException):
        await api.async_get_access_token()


async def test_access_token_successful(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth
) -> None:
    mock_token_manager.async_get_access_token = AsyncMock(return_value="valid_token_123")

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    access_token = await api.async_get_access_token()
    assert access_token == "valid_token_123"


@pytest.fixture
def mock_client_session() -> AsyncMock:
    return AsyncMock(spec=ClientSession)


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    return AsyncMock(spec=VolvoCarsAuth)
