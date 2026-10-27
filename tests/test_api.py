"""API tests."""

from datetime import UTC, datetime
import logging
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientResponseError, ClientSession, RequestInfo
import pytest

from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.auth import VolvoCarsAuth
from volvocarsapi.models import (
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsCommandResult,
)

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


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, VolvoAuthException),
        (403, VolvoAuthException),
        (415, VolvoApiException),
        (500, VolvoApiException),
    ],
)
async def test_failure_exposes_status(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth,
    status: int,
    exception: type[VolvoApiException],
) -> None:
    """Test the HTTP status is exposed on the raised exception."""
    _mock_response_failure(mock_client_session, status)

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(exception) as exc_info:
        await api.async_execute_command("flash")

    assert exc_info.value.status == status


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

    with pytest.raises(VolvoAuthException) as exc_info:
        await api.async_get_access_token()

    assert exc_info.value.status == status


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

    with pytest.raises(VolvoApiException) as exc_info:
        await api.async_get_access_token()

    assert not isinstance(exc_info.value, VolvoAuthException)
    assert exc_info.value.status == status


async def test_redacted_url(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test if request url is redacted in logs."""
    odometer_json = load_json_fixture("odometer")
    _mock_response(mock_client_session, odometer_json)

    vin = "YV1ABCDEFG1234567"
    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey", vin)

    with caplog.at_level(logging.DEBUG):
        await api.async_get_odometer()
        assert "Request [odometer]:" in caplog.text
        assert vin not in caplog.text


async def test_execute_command_sends_no_body(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command is sent without body by default."""
    _mock_response(mock_client_session, _command_json())

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    result = await api.async_execute_command("flash")
    assert result is not None
    assert result.invoke_status == "COMPLETED"
    assert _sent_bodies(mock_client_session) == [None]


async def test_execute_command_falls_back_to_empty_object_on_415(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command is retried with `{}` on 415 and remembers it."""
    mock_client_session.request.side_effect = [
        _create_response_error(415),
        _create_response(_command_json()),
        _create_response(_command_json()),
    ]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    result = await api.async_execute_command("flash")
    assert result is not None
    assert result.invoke_status == "COMPLETED"

    await api.async_execute_command("honk")
    assert _sent_bodies(mock_client_session) == [None, {}, {}]


async def test_execute_command_switches_back_to_no_body_on_415(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command switches back to no body when `{}` starts failing."""
    mock_client_session.request.side_effect = [
        _create_response_error(415),
        _create_response(_command_json()),
        _create_response_error(415),
        _create_response(_command_json()),
        _create_response(_command_json()),
    ]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    await api.async_execute_command("flash")
    await api.async_execute_command("flash")
    await api.async_execute_command("flash")
    assert _sent_bodies(mock_client_session) == [None, {}, {}, None, None]


async def test_execute_command_raises_when_both_variants_fail(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command raises when both body variants are rejected."""
    mock_client_session.request.side_effect = [
        _create_response_error(415),
        _create_response_error(415),
    ]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException) as exc_info:
        await api.async_execute_command("flash")

    assert exc_info.value.status == 415
    assert _sent_bodies(mock_client_session) == [None, {}]


async def test_execute_command_does_not_retry_other_errors(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command is not retried on errors other than 415."""
    mock_client_session.request.side_effect = [_create_response_error(500)]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException):
        await api.async_execute_command("flash")

    assert _sent_bodies(mock_client_session) == [None]


async def test_execute_command_with_body_does_not_retry(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test command with explicit body is not retried on 415."""
    mock_client_session.request.side_effect = [_create_response_error(415)]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException) as exc_info:
        await api.async_execute_command("climatization-start", {"foo": "bar"})

    assert exc_info.value.status == 415
    assert _sent_bodies(mock_client_session) == [{"foo": "bar"}]


@pytest.mark.parametrize("body", [None, {"foo": "bar"}])
async def test_execute_command_returns_unknown_on_422(
    mock_client_session: ClientSession,
    mock_token_manager: VolvoCarsAuth,
    body: dict | None,
) -> None:
    """Test command returns an `UNKNOWN` result on 422."""
    mock_client_session.request.side_effect = [_create_response_error(422)]

    vin = "YV1ABCDEFG1234567"
    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey", vin)

    result = await api.async_execute_command("flash", body)
    assert result == VolvoCarsCommandResult(
        vin=vin, invoke_status="UNKNOWN", message=""
    )
    assert _sent_bodies(mock_client_session) == [body]


async def test_execute_command_remembers_fallback_body_on_422(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test a 422 on the `{}` retry still remembers `{}` as working body."""
    mock_client_session.request.side_effect = [
        _create_response_error(415),
        _create_response_error(422),
        _create_response(_command_json()),
    ]

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    result = await api.async_execute_command("flash")
    assert result is not None
    assert result.invoke_status == "UNKNOWN"

    await api.async_execute_command("flash")
    assert _sent_bodies(mock_client_session) == [None, {}, {}]


async def test_get_commands_raises_on_422(
    mock_client_session: ClientSession, mock_token_manager: VolvoCarsAuth
) -> None:
    """Test 422 on non-command-execution requests is raised."""
    _mock_response_failure(mock_client_session, 422)

    api = VolvoCarsApi(mock_client_session, mock_token_manager, "secretapikey")

    with pytest.raises(VolvoApiException) as exc_info:
        await api.async_get_commands()

    assert exc_info.value.status == 422


def _mock_response(mock_client_session: ClientSession, json: dict) -> None:
    mock_client_session.request.return_value = _create_response(json)


def _mock_response_failure(mock_client_session: ClientSession, status: int) -> None:
    mock_client_session.request.side_effect = ClientResponseError(
        RequestInfo(url="http://127.0.0.1", method="GET", headers={}),
        None,
        status=status,
    )


def _create_response(json: dict) -> AsyncMock:
    response = MagicMock()
    response.json = AsyncMock(return_value=json)

    mock_response = AsyncMock()
    mock_response.__aenter__.return_value = response
    return mock_response


def _create_response_error(status: int) -> ClientResponseError:
    return ClientResponseError(
        RequestInfo(url="http://127.0.0.1", method="POST", headers={}),
        None,
        status=status,
    )


def _command_json() -> dict:
    return {
        "data": {"vin": "YV1ABCDEFG1234567", "invokeStatus": "COMPLETED", "message": ""}
    }


def _sent_bodies(mock_client_session: ClientSession) -> list:
    return [c.kwargs["json"] for c in mock_client_session.request.call_args_list]
