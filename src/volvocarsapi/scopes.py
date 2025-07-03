"""Volvo Cars API scopes."""

from enum import StrEnum


class RestrictedScope(StrEnum):
    """Privacy and security related scopes."""

    LOCK = "conve:lock"
    UNLOCK = "conve:unlock"
    ENGINE_START_STOP = "conve:engine_start_stop"
    HONK_FLASH = "conve:honk_flash"
    LOCATION = "location:read"

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
    "energy:state:read"
]

DEPRECATED_SCOPES = [
    "energy:battery_charge_level",
    "energy:charging_connection_status",
    "energy:charging_current_limit",
    "energy:charging_system_status",
    "energy:electric_range",
    "energy:estimated_charging_time",
    "energy:recharge_status",
    "energy:target_battery_level",
]

ALL_SCOPES = DEFAULT_SCOPES + [s.value for s in RestrictedScope]
