"""Volvo Cars API."""

from http import HTTPStatus
import logging
from typing import Any, cast

from aiohttp import (
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    RequestInfo,
    hdrs,
)
from yarl import URL

from .auth import AccessTokenManager
from .models import (
    VolvoApiException,
    VolvoAuthException,
    VolvoCarsAvailableCommand,
    VolvoCarsCommandResult,
    VolvoCarsErrorResult,
    VolvoCarsLocation,
    VolvoCarsValue,
    VolvoCarsValueField,
    VolvoCarsValueStatusField,
    VolvoCarsVehicle,
)
from .util import redact_data, redact_url

_API_CONNECTED_ENDPOINT = "/connected-vehicle/v2/vehicles"
_API_ENERGY_ENDPOINT = "/energy/v1/vehicles"
_API_ENERGY_V2_ENDPOINT = "/energy/v2/vehicles"
_API_LOCATION_ENDPOINT = "/location/v1/vehicles"
_API_URL = "https://api.volvocars.com"
_API_STATUS_URL = "https://public-developer-portal-bff.weu-prod.ecpaz.volvocars.biz/api/v1/backend-status"
_API_REQUEST_TIMEOUT = ClientTimeout(total=30)

_DATA_TO_REDACT = [
    "coordinates",
    "heading",
    "href",
    "vin",
]

_LOGGER = logging.getLogger(__name__)


class VolvoCarsApi:
    """Volvo Cars API."""

    def __init__(
        self,
        client: ClientSession,
        token_manager: AccessTokenManager,
        api_key: str,
        vin: str = "",
    ) -> None:
        """Initialize Volvo Cars API."""
        self._client = client
        self._token_manager = token_manager
        self.api_key = api_key
        self.vin = vin

    async def async_get_api_status(self) -> dict[str, VolvoCarsValue]:
        """Check the API status."""
        try:
            _LOGGER.debug("Request [API status]")
            async with self._client.get(
                _API_STATUS_URL, timeout=_API_REQUEST_TIMEOUT
            ) as response:
                _LOGGER.debug("Request [API status] status: %s", response.status)
                response.raise_for_status()
                json = await response.json()
                data = cast(dict[str, Any], json)
                _LOGGER.debug("Request [API status] response: %s", data)

                message = data.get("message") or "OK"

        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [API status] error: %s", ex)
            message = "Unknown"

        return {"apiStatus": VolvoCarsValue(message)}

    async def async_get_brakes_status(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get brakes status.

        Required scopes: openid conve:brake_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "brakes", vin)

    async def async_get_command_accessibility(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get availability status.

        Required scopes: openid conve:command_accessibility
        """
        return await self._async_get_field(
            _API_CONNECTED_ENDPOINT, "command-accessibility", vin
        )

    async def async_get_commands(
        self, vin: str = ""
    ) -> list[VolvoCarsAvailableCommand | None]:
        """Get available commands.

        Required scopes: openid conve:commands
        """
        body = await self._async_get(_API_CONNECTED_ENDPOINT, "commands", vin)
        items = self._get_data_list(body)
        return [VolvoCarsAvailableCommand.from_dict(item) for item in items]

    async def async_get_diagnostics(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get diagnostics.

        Required scopes: openid conve:diagnostics_workshop
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "diagnostics", vin)

    async def async_get_doors_status(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get doors status.

        Required scopes: openid conve:doors_status conve:lock_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "doors", vin)

    async def async_get_energy_capabilities(self, vin: str = "") -> dict[str, Any]:
        """Get energy state.

        Required scopes: openid energy:capability:read
        """
        return await self._async_get_data_dict(
            _API_ENERGY_V2_ENDPOINT, "capabilities", vin, data_key="getEnergyState"
        )

    async def async_get_energy_state(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueStatusField | None]:
        """Get energy state.

        Required scopes: openid energy:state:read
        """
        body = await self._async_get(_API_ENERGY_V2_ENDPOINT, "state", vin)
        return {
            key: VolvoCarsValueStatusField.from_dict(value)
            for key, value in body.items()
        }

    async def async_get_engine_status(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get engine status.

        Required scopes: openid conve:engine_status
        """
        return await self._async_get_field(
            _API_CONNECTED_ENDPOINT, "engine-status", vin
        )

    async def async_get_engine_warnings(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get engine warnings.

        Required scopes: openid conve:diagnostics_engine_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "engine", vin)

    async def async_get_fuel_status(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get fuel status.

        Required scopes: openid conve:fuel_status conve:battery_charge_level
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "fuel", vin)

    async def async_get_location(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsLocation | None]:
        """Get location.

        Required scopes: openid location:read
        """
        data = await self._async_get_data_dict(_API_LOCATION_ENDPOINT, "location", vin)
        return {"location": VolvoCarsLocation.from_dict(data)}

    async def async_get_odometer(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get odometer.

        Required scopes: openid conve:odometer_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "odometer", vin)

    async def async_get_recharge_status(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get recharge status.

        Required scopes: openid

        And at least one of:
            energy:recharge_status energy:battery_charge_level energy:electric_range
            energy:estimated_charging_time energy:charging_connection_status
            energy:charging_system_status energy:charging_current_limit
            energy:target_battery_level
        """
        return await self._async_get_field(_API_ENERGY_ENDPOINT, "recharge-status", vin)

    async def async_get_statistics(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get statistics.

        Required scopes: openid conve:trip_statistics
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "statistics", vin)

    async def async_get_tyre_states(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get tyre states.

        Required scopes: openid conve:tyre_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "tyres", vin)

    async def async_get_vehicles(self) -> list[str]:
        """Get vehicles.

        Required scopes: openid conve:vehicle_relation
        """
        url = f"{_API_URL}{_API_CONNECTED_ENDPOINT}"
        body = await self._async_request(hdrs.METH_GET, url, operation="vehicles")
        items = self._get_data_list(body)
        return [item["vin"] for item in items]

    async def async_get_vehicle_details(self, vin: str = "") -> VolvoCarsVehicle | None:
        """Get vehicle details.

        Required scopes: openid conve:vehicle_relation
        """
        data = await self._async_get_data_dict(_API_CONNECTED_ENDPOINT, "", vin)
        return VolvoCarsVehicle.from_dict(data)

    async def async_get_warnings(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get warnings.

        Required scopes: openid conve:warnings
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "warnings", vin)

    async def async_get_window_states(
        self, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        """Get window states.

        Required scopes: openid conve:windows_status
        """
        return await self._async_get_field(_API_CONNECTED_ENDPOINT, "windows", vin)

    async def async_execute_command(
        self, command: str, body: dict[str, Any] | None = None, vin: str = ""
    ) -> VolvoCarsCommandResult | None:
        """Execute a command.

        Required scopes: openid

        Per command:
        - engine-start: conve:engine_start_stop
        - engine-stop: conve:engine_start_stop
        - flash: conve:honk_flash
        - honk: conve:honk_flash
        - honk-flash: conve:honk_flash
        - lock: conve:lock
        - lock-reduced-guard: conve:lock
        - unlock: conve:unlock
        """
        body = await self._async_post(
            _API_CONNECTED_ENDPOINT, f"commands/{command}", body=body, vin=vin
        )
        data: dict = body.get("data", {})
        data["invoke_status"] = data.pop("invokeStatus", None)
        return VolvoCarsCommandResult.from_dict(data)

    async def async_get_access_token(self) -> str:
        """Get or refresh the access token."""
        operation = "token refresh"
        try:
            return await self._token_manager.async_get_access_token()
        except ClientResponseError as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.message)

            # Volvo returns a 400 for a stale refresh token. In such cases we also
            # want to raise a VolvoAuthException.
            if ex.status in (
                HTTPStatus.BAD_REQUEST,
                HTTPStatus.UNAUTHORIZED,
                HTTPStatus.FORBIDDEN,
            ):
                raise VolvoAuthException(ex.message, operation) from ex

            raise VolvoApiException(ex.message, operation) from ex
        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoApiException(ex.__class__.__name__, operation) from ex

    async def _async_get_field(
        self, endpoint: str, operation: str, vin: str = ""
    ) -> dict[str, VolvoCarsValueField | None]:
        body = await self._async_get(endpoint, operation, vin)
        data: dict = body.get("data", {})
        return {
            key: VolvoCarsValueField.from_dict(value) for key, value in data.items()
        }

    async def _async_get_data_dict(
        self, endpoint: str, operation: str, vin: str = "", *, data_key: str = "data"
    ) -> dict[str, Any]:
        body = await self._async_get(endpoint, operation, vin)
        return cast(dict[str, Any], body.get(data_key, {}))

    async def _async_get(
        self, endpoint: str, operation: str, vin: str = ""
    ) -> dict[str, Any]:
        url = self._create_vin_url(endpoint, operation, vin)
        return await self._async_request(
            hdrs.METH_GET, url, operation=operation, vin=vin
        )

    async def _async_post(
        self,
        endpoint: str,
        operation: str,
        *,
        body: dict[str, Any] | None = None,
        vin: str = "",
    ) -> dict[str, Any]:
        url = self._create_vin_url(endpoint, operation, vin)
        return await self._async_request(
            hdrs.METH_POST, url, operation=operation, body=body, vin=vin
        )

    def _get_data_list(self, body: dict[str, Any]) -> list[Any]:
        return cast(list[Any], body.get("data", []))

    def _create_vin_url(self, endpoint: str, operation: str, vin: str = "") -> str:
        if not vin:
            vin = self.vin

        return (
            f"{_API_URL}{endpoint}/{vin}/{operation}"
            if operation
            else f"{_API_URL}{endpoint}/{vin}"
        )

    async def _async_request(
        self,
        method: str,
        url: str,
        *,
        operation: str,
        body: dict[str, Any] | None = None,
        vin: str = "",
    ) -> dict[str, Any]:
        access_token = await self.async_get_access_token()

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {access_token}",
            "vcc-api-key": self.api_key,
        }

        if method == hdrs.METH_POST:
            headers[hdrs.CONTENT_TYPE] = "application/json"

        data: dict[str, Any] = {}

        try:
            _LOGGER.debug(
                "Request [%s]: %s %s",
                operation,
                method,
                redact_url(url, vin),
            )
            async with self._client.request(
                method, url, headers=headers, json=body, timeout=_API_REQUEST_TIMEOUT
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
        except ClientResponseError as ex:
            if ex.status == HTTPStatus.NOT_FOUND:
                return {}

            _LOGGER.debug("Request [%s] error: %s", operation, ex.message)

            if ex.status == HTTPStatus.UNPROCESSABLE_ENTITY and "/commands" in url:
                return {
                    "data": {
                        "vin": vin,
                        "invokeStatus": "UNKNOWN",
                        "message": "",
                    }
                }

            redacted_exception = RedactedClientResponseError(ex, vin)
            message = redacted_exception.message

            if data and (error_data := data.get("error")):
                error = VolvoCarsErrorResult.from_dict(error_data)

                if error is not None:
                    message = f"{error.message} {error.description}".strip()

            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise VolvoAuthException(message, operation) from redacted_exception

            raise VolvoApiException(message, operation) from redacted_exception

        except (ClientError, TimeoutError) as ex:
            _LOGGER.debug("Request [%s] error: %s", operation, ex.__class__.__name__)
            raise VolvoApiException(ex.__class__.__name__, operation) from ex


class RedactedClientResponseError(ClientResponseError):
    """Exception class that redacts sensitive data."""

    def __init__(self, exception: ClientResponseError, vin: str) -> None:
        """Initialize class."""

        redacted_url = self._redact_url(exception.request_info.url, vin)
        redacted_real_url = self._redact_url(exception.request_info.real_url, vin)
        redacted_request_info = RequestInfo(
            redacted_url,
            exception.request_info.method,
            exception.request_info.headers,
            redacted_real_url,
        )

        super().__init__(
            redacted_request_info,
            exception.history,
            status=exception.status,
            message=exception.message,
            headers=exception.headers,
        )

    def _redact_url(self, url: URL, vin: str) -> URL:
        redacted_url = redact_url(str(url), vin)
        return URL(redacted_url)
