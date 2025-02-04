import requests
import json
from typing import List
from model.Location import Location
from model.Coordinates import Coordinates


class TravelTimes:
    """
    Stores travel times between locations, using OpenRouteService data.
    """

    def __init__(self, auth_key: str, locations: List[Location]):
        """
        Initializes the TravelTimes with travel times between all pairs of locations.

        Args:
            auth_key (str): The authentication key for the travel time service.
            locations (List[Location]): The list of locations.
        """
        travel_times = self._get_travel_times(auth_key, [loc.coordinates for loc in locations])
        self.travel_times = {}
        self.max_travel_time = travel_times[0][0]
        self.max_pair = locations[0], locations[0]
        
        for i, loc1 in enumerate(locations):
            self.travel_times[loc1] = {}
            for j, loc2 in enumerate(locations):
                self.travel_times[loc1][loc2] = travel_times[i][j]
                if travel_times[i][j] > self.max_travel_time:
                    self.max_travel_time = travel_times[i][j]
                    self.max_pair = loc1, loc2

    def _get_travel_times(self, auth_key: str, coords: List[Coordinates]) -> List[List[float]]:
        """
        Gets travel times between locations using the OpenRouteService API.

        Args:
            auth_key (str): The authentication key for the travel time service.
            coords (List[Coordinates]): The list of coordinates.

        Returns:
            List[List[float]]: A matrix of travel times between the locations.
        """
        measurement = ["distance", "duration"][1]
        transport_mode = ["foot-walking", "cycling-regular", "driving-car"][0]
        body = {
            "locations": [(c.lon, c.lat) for c in coords],
            "destinations": list(range(len(coords))),
            "metrics": [measurement]
        }
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': auth_key
        }
        call = requests.post(
            f"https://api.openrouteservice.org/v2/matrix/{transport_mode}",
            json=body,
            headers=headers
        )
        return call.json()[measurement + 's']