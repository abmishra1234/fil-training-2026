"""Unit conversions with input validation."""

KM_PER_MILE = 1.609344


def km_to_miles(km: float) -> float:
    if km < 0:
        raise ValueError("distance cannot be negative")
    return round(km / KM_PER_MILE, 3)


def miles_to_km(miles: float) -> float:
    if miles < 0:
        raise ValueError("distance cannot be negative")
    return round(miles * KM_PER_MILE, 3)


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9 / 5 + 32, 2)


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32) * 5 / 9, 2)
