"""Test fixtures."""

from unittest.mock import AsyncMock

from aiohttp import ClientSession
import pytest

from volvocarsapi.auth import VolvoCarsAuth


@pytest.fixture
def mock_client_session() -> AsyncMock:
    """Mock client session."""
    return AsyncMock(spec=ClientSession)


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    """Mock token manager."""

    def _create_mock() -> VolvoCarsAuth:
        return AsyncMock(spec=VolvoCarsAuth)

    mock = _create_mock()
    mock.async_get_access_token = AsyncMock(return_value="valid_token_123")

    return mock
