import requests
import json
from typing import Any, Optional
from typing_extensions import Self
from model.Coordinates import Coordinates


class Location:
    """
    Represents a location with coordinates.
    """
    
    def __init__(self, coordinates: Coordinates):
        """
        Initializes the Location with coordinates.

        Args:
            coordinates (Coordinates): The coordinates of the location.
        """
        self.coordinates = coordinates

    def __eq__(self, other: Any) -> bool:
        """
        Checks if two Location instances are equal based on their coordinates.

        Args:
            other (Any): The other object to compare.

        Returns:
            bool: True if the coordinates are equal, False otherwise.
        """
        if type(other) is type(self):
            return (self.coordinates.lon == other.coordinates.lon and 
                    self.coordinates.lat == other.coordinates.lat)
        return False

    def __hash__(self) -> int:
        """
        Returns a hash value based on the coordinates.

        Returns:
            int: The hash value.
        """
        return hash((self.coordinates.lon, self.coordinates.lat))

    @classmethod
    def from_address(cls,
                     auth_key: str,
                     country_code: str,
                     address: str,
                     focus: Optional[Coordinates] = None) -> Self:
        """
        Creates a Location instance from an address using a geocoding service.

        Args:
            auth_key (str): The authentication key for the geocoding service.
            country_code (str): The country code.
            address (str): The address to geocode.
            focus (Optional[Coordinates]): Optional focus coordinates to bias the geocoding.

        Returns:
            Location: The created Location instance.

        Raises:
            RuntimeError: If there is an error in the geocoding response.
        """
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8'
        }
        call = requests.get(
            'https://api.openrouteservice.org/geocode/search?'
            f'api_key={auth_key}&'
            f'text={address}&'
            + (f'focus.point.lon={focus.lon}&' if focus else '')
            + (f'focus.point.lat={focus.lat}&' if focus else '')
            + f'boundary.country={country_code}&'
            'size=1',
            headers=headers
        )
        result = json.loads(call.text)
        if "error" in result:
            raise RuntimeError(f"Openrouteservice: {result['error']}")
        lon_lat = result["features"][0]["geometry"]["coordinates"]
        lat_lon = list(reversed(lon_lat))
        return cls(Coordinates(*lat_lon))