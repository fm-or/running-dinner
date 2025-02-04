from typing import Dict, List, Tuple, Optional
from time import perf_counter
import folium
from folium.plugins import TagFilterButton
from model.Group import Group
from model.Location import Location
from model.TravelTimes import TravelTimes
from pulp import LpVariable, LpBinary, LpInteger, LpContinuous, LpProblem, LpMinimize, LpStatus, lpSum, listSolvers, getSolver, PULP_CBC_CMD

class DinnerInstance:

    def __init__(self,
                 ors_auth_key: str,
                 country_code: str,
                 city_address: str,
                 events: List[str],
                 addresses: List[Tuple[str, str, int]],
                 party_address: Optional[str] = None) -> None:
        """
        Sets up a DinnerInstance by geocoding the main city address and optional
        party address, validating the event list, and creating group objects from
        the given addresses. Each address tuple consists of the group’s name,
        the local address, and the event ID that group wants to host.

        At least three events are required (e.g., a start event, at least one
        main event, and a final event), and each event must have at least one
        hosting group. If a party address is provided, it is also geocoded
        and included for subsequent calculations.

        Args:
            ors_auth_key (str): The authentication key for the OpenRouteService API.
            country_code (str): The country code (alpha-2 or alpha-3) for geocoding.
            city_address (str): The primary city address where the dinner event is centered.
            events (List[str]): Ordered list of event names, with at least three entries.
            addresses (List[Tuple[str, str, int]]): A list of (group name, address, event ID).
            party_address (Optional[str]): Optional address for an after-party. Defaults to None.

        Raises:
            ValueError: If fewer than three events are given or if any event has no groups hosting it.
        """
        self.country_code = country_code
        self.city_address = city_address
        self.city_location = Location.from_address(auth_key=ors_auth_key, country_code=country_code, address=city_address)
        if len(events) < 3:
            raise ValueError("There must be a starting and ending event and at least one main event in between.")
        self.events = events
        addresses.sort(key=lambda address: address[2])
        self.groups = Group.from_dict(ors_auth_key,
                                      country_code,
                                      self.city_location,
                                      map(lambda address: (address[0], city_address + ", " + address[1], address[2]), addresses))
        self.hosts_by_events = {e: list() for e in range(1, len(events)-1)}
        for group in self.groups:
            self.hosts_by_events[group.host_event_id].append(group)
        for e in range(1, len(events)-1):
            if len(self.hosts_by_events[e]) == 0:
                raise ValueError(f"There must be at least one host for event {events[e]}.")
        self.after_party = Location.from_address(ors_auth_key, country_code, city_address + ", " + party_address, self.city_location.coordinates) if party_address is not None else None
        self.all_locations = Group.get_locations(self.groups)
        if self.after_party:
            self.all_locations.append(self.after_party)
        self.travel_times = TravelTimes(auth_key=ors_auth_key, locations=self.all_locations)

    def solve(self,
              penalty_too_few_guests: int = 600,
              penalty_too_many_guests: int = 600,
              penalty_multiple_encounters: int = 600,
              prioritized_solver_str: Optional[str] = None) -> Dict[Group, List[Group]]:
        """
        Solves the dinner instance optimization problem by assigning each group
        to hosting and visiting other groups according to the specified events.

        Each host is expected to have exactly two guests at its event. Penalties
        are applied if there are fewer or more than two guests, and additional
        penalties apply if the same groups meet more than once.

        If a specific solver is requested and available in PuLP, that solver will
        be used; otherwise, the default solver is used.

        Args:
            penalty_too_few_guests (int): The penalty for having fewer than two guests
                at a hosted event. Default is 600.
            penalty_too_many_guests (int): The penalty for having more than two guests
                at a hosted event. Default is 600.
            penalty_multiple_encounters (int): The penalty for multiple encounters
                between the same groups. Default is 600.
            prioritized_solver_str (Optional[str]): If provided and recognized by PuLP,
                the corresponding solver will be prioritized. Default is None.

        Returns:
            Dict[Group, List[Group]]: A dictionary mapping each group to a sorted list
            of the hosts that the group visits (including itself if it is hosting).

        Raises:
            PuLPError: If an error occurs while solving with the selected solver.
        """
        # Assignment variables
        x = dict()
        for group in self.groups:
            for host in self.groups:
                x[group, host] = LpVariable(f"x[{group.name},{host.name}]", cat=LpBinary)

        # Maximum travel time variables
        t = dict()
        for e in range(len(self.events) - 1):
            t[e] = LpVariable(f"t[{e}]", lowBound=0, cat=LpContinuous)

        # auxiliary variable to check if two teams meet at one location
        y = dict()
        for g1 in range(len(self.groups)-1):
            for g2 in range(g1+1, len(self.groups)):
                for host in self.groups:
                    y[self.groups[g1], self.groups[g2], host] = LpVariable("y[{0},{1},{2}]".format(self.groups[g1].name, self.groups[g2].name, host.name), cat=LpBinary)

        # auxiliary variable for penalties
        z = dict()
        for host in self.groups:
            z[1, host] = LpVariable("z[1,{0}]".format(host.name), cat=LpBinary)
        for host in self.groups:
            z[2, host] = LpVariable("z[2,{0}]".format(host.name), cat=LpBinary)
        for g1 in range(len(self.groups)-1):
            for g2 in range(g1+1, len(self.groups)):
                z[3, self.groups[g1], self.groups[g2]] = LpVariable("z[3,{0},{1}]".format(self.groups[g1].name, self.groups[g2].name), cat=LpInteger)

        # initialize problem
        start_perf_counter = perf_counter()
        prob = LpProblem("Running-Dinner", LpMinimize)

        # objective function
        prob += lpSum(t[e] for e in range(len(self.events)-1)) +\
                + penalty_too_few_guests * lpSum(z[1, host] for host in self.groups) +\
                + penalty_too_many_guests * lpSum(z[2, host] for host in self.groups) +\
                + penalty_multiple_encounters * lpSum(z[3, self.groups[g1], self.groups[g2]] for g1 in range(len(self.groups)-1) for g2 in range(g1+1, len(self.groups)))

        # link from assignment to travel time variables
        for group in self.groups:
            # travel times after start event: each group start from its home
            prob += lpSum(self.travel_times.travel_times[group.location][host.location] * x[group, host]
                        for host in self.hosts_by_events[1]
                        ) <= t[0]
            # travel times between main events
            for e in range(1, len(self.events)-2):
                for host1 in self.hosts_by_events[e]:
                    for host2 in self.hosts_by_events[e+1]:
                        prob += self.travel_times.travel_times[host1.location][host2.location] * (x[group, host1] + x[group, host2] - 1) <= t[e]
            # travel times to end event
            if self.after_party is None:
                # each group travels to its home
                prob += lpSum(self.travel_times.travel_times[host.location][group.location] * x[group, host]
                        for host in self.hosts_by_events[len(self.events)-2]
                        ) <= t[len(self.events)-2]
            else:
                # each group travels to the party location
                prob += lpSum(self.travel_times.travel_times[host.location][self.after_party]
                        for host in self.hosts_by_events[len(self.events)-2]
                        ) <= t[len(self.events)-2]
        
        # each group must visit exactly one group for each main event
        for group in self.groups:
            for e in range(1, len(self.events)-1):
                prob += lpSum(x[group, host]
                            for host in self.hosts_by_events[e]
                            ) == 1
        
        # each group visits itself when it hosts
        for group in self.groups:
            prob += x[group, group] == 1

        # if a group is hosting an event, three groups must be present. Deviations are penalized.
        for host in self.groups:
            prob += lpSum(x[group, host] for group in self.groups) == 3 - z[1, host] + z[2, host]

        # count how often teams meet during the main events
        for g1 in range(len(self.groups)-1):
            for g2 in range(g1+1, len(self.groups)):
                for host in self.groups:
                    prob += x[self.groups[g1], host] + x[self.groups[g2], host] <= 1 + y[self.groups[g1], self.groups[g2], host]

        # teams may only meet up to once. More meetings are penalized.
        for g1 in range(len(self.groups)-1):
            for g2 in range(g1+1, len(self.groups)):
                for host in self.groups:
                    prob += lpSum(y[self.groups[g1], self.groups[g2], host] for host in self.groups) <= 1 + z[3, self.groups[g1], self.groups[g2]]

        # check for solvers
        selected_solver = PULP_CBC_CMD(msg=0)
        if prioritized_solver_str is not None and prioritized_solver_str in listSolvers():
            prioritized_solver = getSolver(prioritized_solver_str, msg=0)
            if prioritized_solver.available:
                selected_solver = prioritized_solver
        status = prob.solve(selected_solver)

        print(f"{LpStatus[status]} in {round(perf_counter() - start_perf_counter, 2)} seconds by {selected_solver.name}.")

        return {group: sorted([host for host in self.groups if x[group, host].value() > 0.99], key=lambda host: host.host_event_id) for group in self.groups}
    
    def save_csv(self, filename: str, solution: Dict[Group, List[Group]]) -> None:
        """
        Saves the solution to a CSV file.

        Args:
            filename (str): The name of the file to save the CSV to.
            solution (Dict[Group, List[Group]]): The solution containing groups and their hosts.
        """
        with open(filename, "w") as file:
            file.write('"Group";"{0}"\n'.format('";"'.join(self.events[1:-1])))
            for group, hosts in solution.items():
                file.write('"{0}";"{1}"\n'.format(group.name, '";"'.join(host.name for host in hosts)))
    
    def save_map(self, filename: str, solution: Dict[Group, List[Group]]) -> None:
        """
        Saves a map with the locations of the groups and the after party.

        Args:
            filename (str): The name of the file to save the map to.
            solution (Dict[Group, List[Group]]): The solution containing groups and their hosts.
        """
        # Find the center of the map
        min_lat, min_lon, max_lat, max_lon = None, None, None, None
        for location in self.all_locations:
            if min_lat is None or location.coordinates.lat < min_lat:
                min_lat = location.coordinates.lat
            if min_lon is None or location.coordinates.lon < min_lon:
                min_lon = location.coordinates.lon
            if max_lat is None or location.coordinates.lat > max_lat:
                max_lat = location.coordinates.lat
            if max_lon is None or location.coordinates.lon > max_lon:
                max_lon = location.coordinates.lon
        map_center = (min_lat + max_lat) / 2, (min_lon + max_lon) / 2

        # Create a map
        mymap = folium.Map(location=map_center, zoom_start=15, tiles='OpenStreetMap')

        party_event = ["Party"] if self.after_party is not None else list()

        # Add markers for each address
        for group, hosts in solution.items():
            folium.Marker(
                location = [group.location.coordinates.lat, group.location.coordinates.lon],
                popup = f"<nobr>{group.name}: {self.events[group.host_event_id]}</nobr>",
                tags = [group.name],
                icon=folium.Icon(icon=str(group.host_event_id), prefix="fa", color="green")
            ).add_to(mymap)
            for host in hosts:
                if host != group:
                    folium.Marker(
                        location = [host.location.coordinates.lat, host.location.coordinates.lon],
                        popup = f"<nobr>{host.name}: {self.events[host.host_event_id]}</nobr>",
                        tags = [group.name],
                        icon=folium.Icon(icon=str(host.host_event_id), prefix="fa", color="orange")
                    ).add_to(mymap)
        for group, hosts in solution.items():
            for other_group in self.groups:
                if other_group not in hosts:
                    folium.Marker(
                        location = [other_group.location.coordinates.lat, other_group.location.coordinates.lon],
                        popup = f"<nobr>{other_group.name}: {self.events[other_group.host_event_id]}</nobr>",
                        tags = [group.name],
                        icon=folium.Icon(icon="user", color="gray")
                    ).add_to(mymap)
        # Add a marker for the after party if there is any
        if self.after_party is not None:
            folium.Marker(
                location=[self.after_party.coordinates.lat, self.after_party.coordinates.lon],
                popup=folium.Popup(f"<nobr>Party: {self.events[-1]}</nobr>"),
                icon=folium.Icon(icon="music", color="red")
            ).add_to(mymap)

        # Add lines for the solution
        for group, hosts in solution.items():
            folium.PolyLine(
                locations=[
                    [group.location.coordinates.lat, group.location.coordinates.lon],
                    [hosts[0].location.coordinates.lat, hosts[0].location.coordinates.lon]
                ],
                tags=[group.name]
            ).add_to(mymap)

            for i in range(len(hosts)-1):
                folium.PolyLine(
                    locations=[
                        [hosts[i].location.coordinates.lat, hosts[i].location.coordinates.lon],
                        [hosts[i+1].location.coordinates.lat, hosts[i+1].location.coordinates.lon]
                    ],
                    tags=[group.name]
                ).add_to(mymap)
            destination = self.after_party if self.after_party is not None else group.location
            folium.PolyLine(
                locations=[
                    [hosts[-1].location.coordinates.lat, hosts[-1].location.coordinates.lon],
                    [destination.coordinates.lat, destination.coordinates.lon]
                ],
                tags=[group.name]
            ).add_to(mymap)

        # Add a tag filter button for each group
        TagFilterButton([group.name for group in self.groups]).add_to(mymap)

        # Save the map
        mymap.save(filename)
