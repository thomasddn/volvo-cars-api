"""Tests for Volvo Cars API models."""

from volvocarsapi.models import VolvoCarsValue, VolvoCarsVehicle


def test_from_dict_returns_none_when_data_is_none() -> None:
    """from_dict returns None when data is None."""
    assert VolvoCarsValue.from_dict(None) is None


def test_from_dict_returns_none_when_data_is_empty() -> None:
    """from_dict returns None when data has no recognised fields."""
    assert VolvoCarsValue.from_dict({}) is None


def test_from_dict_valid_data() -> None:
    """from_dict creates instance from valid data."""
    result = VolvoCarsValue.from_dict({"value": 42})
    assert result is not None
    assert result.value == 42


def test_from_dict_nested_model_with_null_value() -> None:
    """from_dict handles a null nested model value without raising."""
    data = {
        "vin": "YV1ABC123456789",
        "modelYear": 2023,
        "gearbox": "AUTOMATIC",
        "fuelType": "ELECTRIC",
        "images": None,
        "descriptions": {
            "model": "XC40",
            "steering": "LEFT",
        },
    }
    result = VolvoCarsVehicle.from_dict(data)
    assert result is not None
    assert result.vin == "YV1ABC123456789"
    assert result.images is None


def test_from_dict_none_on_nested_model_class() -> None:
    """from_dict on a nested model class also returns None when data is None."""
    from volvocarsapi.models import VolvoCarsImages

    assert VolvoCarsImages.from_dict(None) is None
