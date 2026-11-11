"""Volvo Cars API scopes."""

from enum import StrEnum


class RestrictedScope(StrEnum):
    """Privacy and security related scopes."""

    LOCK = "conve:lock"
    UNLOCK = "conve:unlock"
    ENGINE_START_STOP = "conve:engine_start_stop"
    HONK_FLASH = "conve:honk_flash"
    LOCATION = "location:read"
    WALLBOX_WRITE = "energy_device:wallbox:write"
    WALLBOX_CONTROL = "energy_device:wallbox:control"


# Scopes per type for the new Volvo ID system
OPENID_SCOPES = ["openid"]

# Connected Vehicle API scopes, excluding restricted scopes
CONVE_SCOPES = [
    "conve:battery_charge_level",
    "conve:brake_status",
    "conve:climatization_start_stop",
    "conve:command_accessibility",
    "conve:commands",
    "conve:connectivity_status",
    "conve:diagnostics_engine_status",
    "conve:diagnostics_workshop",
    "conve:doors_status",
    "conve:engine_status",
    "conve:environment",
    "conve:fuel_status",
    "conve:lock_status",
    "conve:navigation",
    "conve:odometer_status",
    "conve:trip_statistics",
    "conve:tyre_status",
    "conve:vehicle_relation",
    "conve:warnings",
    "conve:windows_status",
]

# Energy API scopes
ENERGY_SCOPES = [
    "energy:capability:read",
    "energy:state:read",
]

# Energy device scopes, excluding restricted scopes
ENERGY_DEVICE_SCOPES = [
    "energy_device:user_id_token:readwrite",
    "energy_device:wallbox:read",
]

# Deprecated: use `get_volvoid_server(client_id).default_scopes` and `.all_scopes`
# from `volvocarsapi.auth` instead. These keep the legacy Volvo ID scopes (client IDs
# starting with `dc-`) until the migration deadline has passed, so existing
# applications don't request scopes they were never registered with.
DEFAULT_SCOPES = [
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

ALL_SCOPES = [
    *DEFAULT_SCOPES,
    RestrictedScope.LOCK.value,
    RestrictedScope.UNLOCK.value,
    RestrictedScope.ENGINE_START_STOP.value,
    RestrictedScope.HONK_FLASH.value,
    RestrictedScope.LOCATION.value,
]
