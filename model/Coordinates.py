from typing import NamedTuple


class Coordinates(NamedTuple):
    """
    Represents geographical coordinates.

    Attributes:
        lat (float): The latitude of the location.
        lon (float): The longitude of the location.
    """
    lat: float
    lon: float