import pytest

from converter import celsius_to_fahrenheit, fahrenheit_to_celsius, km_to_miles, miles_to_km


def test_km_to_miles():
    assert km_to_miles(42.195) == 26.219


def test_miles_to_km():
    assert miles_to_km(1) == 1.609


def test_negative_distance_rejected():
    with pytest.raises(ValueError):
        km_to_miles(-1)


@pytest.mark.parametrize(("c", "f"), [(0, 32.0), (100, 212.0), (-40, -40.0), (37, 98.6)])
def test_temperature_round_trip(c, f):
    assert celsius_to_fahrenheit(c) == f
    assert fahrenheit_to_celsius(f) == c
