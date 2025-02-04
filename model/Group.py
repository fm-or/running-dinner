from typing import List, Tuple
from typing_extensions import Self
from model.Location import Location


class Group:
    """
    Represents a group with a name, location, and ...
    """
    
    def __init__(self, name: str, location: Location, host_event_id: int):
        """
        Initializes the Group with a name, location, and size.

        Args:
            name (str): The name of the group.
            location (Location): The location of the group.
            host_event_id (int):
        """
        self.name = name
        self.location = location
        self.host_event_id = host_event_id

    @classmethod
    def from_address(cls, name: str, auth_key: str, country_code: str, address: str, host_event_id: int) -> Self:
        """
        Creates a Group instance from an address.

        Args:
            name (str): The name of the group.
            auth_key (str): The authentication key for the geocoding service.
            country_code (str): The country code.
            address (str): The address to geocode.
            host_event_id (int): 

        Returns:
            Group: The created Group instance.
        """
        location = Location.from_address(auth_key, country_code, address)
        return cls(name, location, host_event_id)

    @classmethod
    def from_dict(cls, auth_key: str, country_code: str, city: Location,
                  addresses: List[Tuple[str, str, int]]) -> List[Self]:
        """
        Creates a list of Group instances from a list of addresses.

        Args:
            auth_key (str): The authentication key for the geocoding service.
            country_code (str): The country code.
            city (Location): The city location to use as a focus for geocoding.
            addresses (List[Tuple[str, str, int]]): A list of tuples containing name,
                address, and ...

        Returns:
            List[Group]: A list of created Group instances.
        """
        groups = list()
        locations = dict()
        for (grp_name, grp_address, grp_host_event_id) in addresses:
            location = Location.from_address(auth_key, country_code, grp_address, focus=city.coordinates)
            if location not in locations:
                locations[location] = location
            groups.append(cls(grp_name, locations[location], grp_host_event_id))
        return groups

    @classmethod
    def get_locations(cls, groups: List[Self]) -> List[Location]:
        """
        Gets unique locations from a list of groups.

        Args:
            groups (List[Group]): The list of groups.

        Returns:
            List[Location]: The list of unique locations.
        """
        return list({group.location for group in groups})