"""Explicit dimensional conversion at the project boundary."""
import math
from pint import UnitRegistry

REGISTRY = UnitRegistry(autoconvert_offset_to_baseunit=True)


def quantity(value, unit):
    if isinstance(value, dict) and set(value) == {"value", "unit"}:
        number = REGISTRY.Quantity(float(value["value"]), value["unit"]).to(unit).magnitude
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        number = float(value)  # bare numbers use the declared schema unit
    else:
        raise ValueError(f"Expected a number or {{value, unit}} in {unit}")
    if not math.isfinite(number):
        raise ValueError("Non-finite quantity")
    return float(number)
