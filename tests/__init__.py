"""Tests for Volvo Cars API."""

from functools import lru_cache
import json
import pathlib
from typing import Any
from unittest.mock import AsyncMock


def configure_mock(
    mock: AsyncMock, *, return_value: Any = None, side_effect: Any = None
) -> None:
    """Reconfigure mock."""
    mock.reset_mock()
    mock.side_effect = side_effect
    mock.return_value = return_value


@lru_cache
def load_json_fixture(name: str) -> dict:
    """Load a JSON object from a fixture."""

    name = f"{name}.json"
    fixtures_path = pathlib.Path().cwd().joinpath("tests", "fixtures")
    data_path = fixtures_path.joinpath(name)

    fixture = data_path.read_text(encoding="utf8")

    return json.loads(fixture)
