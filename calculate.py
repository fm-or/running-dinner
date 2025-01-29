import requests
import json
from typing import List, Tuple, Dict
from typing_extensions import Any, Self
from pulp import *
from time import perf_counter


def get_coordinates_by_address(location: str) -> Tuple[float, float]:
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8'
    }
    authorization = '5b3ce3597851110001cf62484afafd161320478f803cc018ec70f210'
    call = requests.get(
        'https://api.openrouteservice.org/geocode/search?'
        'api_key=' + str(authorization) + '&'
        'text=' + str(location) + '&'
        'focus.point.lon=10.3167616&'
        'focus.point.lat=51.8065205&'
        'boundary.country=DE&'
        'sources=openstreetmap&'
        'layers=address&'
        'size=1',
        headers=headers)
    coordinates = json.loads(call.text)["features"][0]["geometry"]["coordinates"]
    return coordinates


def get_coordinates_by_venue(location: str) -> Tuple[float, float]:
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8'
    }
    authorization = '5b3ce3597851110001cf62484afafd161320478f803cc018ec70f210'
    call = requests.get(
        'https://api.openrouteservice.org/geocode/search?'
        'api_key=' + str(authorization) + '&'
        'text=' + str(location) + '&'
        'focus.point.lon=10.3167616&'
        'focus.point.lat=51.8065205&'
        'boundary.country=DE&'
        'sources=openstreetmap&'
        'layers=venue&'
        'size=1',
        headers=headers)
    coordinates = json.loads(call.text)["features"][0]["geometry"]["coordinates"]
    return coordinates


def get_travel_times(locations: List[Tuple[float, float]]) -> List[List[float]]:
    measurement = ["distance", "duration"][1]
    transport_mode = ["foot-walking", "cycling-regular", "driving-car"][0]
    body = {"locations": locations,
            "destinations": list(range(len(locations))),
            "metrics": [measurement]}
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': '5b3ce3597851110001cf62484afafd161320478f803cc018ec70f210'
    }
    # start = time.time()
    call = requests.post('https://api.openrouteservice.org/v2/matrix/'+transport_mode, json=body, headers=headers)
    return call.json()[measurement+'s']


class Group:

    def __init__(self, name: str, location: str, host_event_id: int):
        self.name = name
        self.location = Location.fromAddress(name, location)
        self.host_event_id = host_event_id

    def __eq__(self, other: Any) -> bool:
        if type(other) is type(self):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)
    
class Location:
    
    def __init__(self, name: str, coordinates):
        self.name = name
        self.coordinates = coordinates

    def __eq__(self, other: Any) -> bool:
        if type(other) is type(self):
            return self.name, self.coordinates == other.name, other.coordinates
        return False

    def __hash__(self) -> int:
        return hash((self.name, self.coordinates[0], self.coordinates[1]))

    @classmethod
    def fromAddress(cls, group_name: str, address: str) -> Self:
        return cls(group_name, get_coordinates_by_address(address))
    
    @classmethod
    def fromVenue(cls, venue: str) -> Self:
        return cls(venue, get_coordinates_by_venue(venue))
    
class TravelTimes:

    def __init__(self, locations: List[Location]):
        travel_times = get_travel_times([location.coordinates for location in locations])
        self.travel_times = dict()
        self.max_travel_time = 0
        self.max_pair = None
        for i in range(len(locations)):
            self.travel_times[locations[i]] = dict()
            for j in range(len(locations)):
                self.travel_times[locations[i]][locations[j]] = travel_times[i][j]
                if travel_times[i][j] > self.max_travel_time:
                    self.max_travel_time = travel_times[i][j]
                    self.max_pair = locations[i], locations[j]


### INPUT DATA ###

events = ["zu Hause", "Vorspeise", "Hauptspeise", "Nachspeise", "After Party"]

print("Getting coordinates...")
groups = list()
groups.append(Group("Group 1", "Am Schlagbaum 25", 1))
groups.append(Group("Group 2", "Großer Bruch 20", 1))
groups.append(Group("Group 3", "Burgstätter Straße 7", 1))
groups.append(Group("Group 4", "Rollstraße 5", 1))
groups.append(Group("Group 5", "Rollstraße 2", 2))
groups.append(Group("Group 6", "Schulstraße 18a", 2))
groups.append(Group("Group 7", "Adolph-Roemer-Straße 7", 2))
# groups.append(Group("Group 8", "Gerhard-Rauschenbach-Straße 4", 3))
groups.append(Group("Group 8", "Schulstraße 18a", 3))
groups.append(Group("Group 9", "Schulstraße 21", 3))
groups.append(Group("Group 10", "Burgstätter Straße 5", 3))
# groups.append(Group("Group 11", "Rollstraße 2", 3))

after_party = "Erzstraße 45"  # no after party: None

p_too_few_cost = 1800
p_too_many_cost = 0
p_too_often_cost = 600


### DATA ORGANIZATION ###
hosts_by_events = {e: list() for e in range(1, len(events)-1)}
for group in groups:
    hosts_by_events[group.host_event_id].append(group)

# sort groups by host event
groups.sort(key=lambda group: group.host_event_id)

locations = [group.location for group in groups]
if after_party is not None:
    locations.append(Location.fromAddress("After Party", after_party))

print("Getting travel times...")
travel_times = TravelTimes(locations)


# check for solvers
availableSolvers = listSolvers(onlyAvailable=True)

# assignment variables
x = dict()
for group in groups:
    for host in groups:
        x[group, host] = LpVariable("x[{0},{1}]".format(group.name, host.name), cat=LpBinary)

# maximum travel time variables
t = dict()
for e in range(len(events)-1):
    t[e] = LpVariable("t[{0}]".format(e), lowBound=0, cat=LpContinuous)

# auxiliary variable to check if two teams meet at one location
y = dict()
for group1 in groups:
    for group2 in groups:
        if group1 != group2:
            for host in groups:
                y[group1, group2, host] = LpVariable("y[{0},{1},{2}]".format(group1.name, group2.name, host.name), cat=LpBinary)

z = dict()
for host in groups:
    z[1, host] = LpVariable("z[1,{0}]".format(host.name), cat=LpBinary)
for host in groups:
    z[2, host] = LpVariable("z[2,{0}]".format(host.name), cat=LpBinary)
for group1 in groups:
    for group2 in groups:
        if group1 != group2:
            z[3, group1, group2] = LpVariable("z[3,{0},{1}]".format(group1.name, group2.name), cat=LpBinary)

# initialize problem
start_perf_counter = perf_counter()
prob = LpProblem("Running-Dinner", LpMinimize)

# objective function
prob += lpSum(t[e] for e in range(len(events)-1)) +\
        + p_too_few_cost * lpSum(z[1, host] for host in groups) +\
        + p_too_many_cost * lpSum(z[2, host] for host in groups) +\
        + p_too_often_cost * lpSum(z[3, group1, group2] for group1 in groups for group2 in groups if group1 != group2)

# link from assignment to travel time variables
for group in groups:
    # travel times after start event: each group start from its home
    prob += lpSum(travel_times.travel_times[group.location][host.location] * x[group, host]
                  for host in hosts_by_events[1]
                  ) <= t[0]
    # travel times between main events
    for e in range(1, len(events)-2):
        for host1 in hosts_by_events[e]:
            for host2 in hosts_by_events[e+1]:
                prob += travel_times.travel_times[host1.location][host2.location] * (x[group, host1] + x[group, host2] - 1) <= t[e]
    # travel times to end event
    if after_party is None:
        # each group travels to its home
        prob += lpSum(travel_times.travel_times[host.location][group.location] * x[group, host]
                  for host in hosts_by_events[len(events)-2]
                  ) <= t[len(events)-2]
    else:
        # each group travels to the party location
        prob += lpSum(travel_times.travel_times[host.location][locations[-1]]
                  for host in hosts_by_events[len(events)-2]
                  ) <= t[len(events)-2]
        
# each group must visit exactly one group for each main event
for group in groups:
    for e in range(1, len(events)-1):
        prob += lpSum(x[group, host]
                    for host in hosts_by_events[e]
                    ) == 1
        
# each group visits itself when it hosts
for group in groups:
    prob += x[group, group] == 1

# if a group is hosting an event, three groups must be present. Deviations are penalized.
for host in groups:
    prob += lpSum(x[group, host] for group in groups) == 3 - z[1, host] + z[2, host]

# count how often teams meet during the main events
for group1 in groups:
    for group2 in groups:
        if group1 != group2:
            for host in groups:
                prob += x[group1, host] + x[group2, host] <= 1 + y[group1, group2, host]

# teams may only meet up to once. More meetings are penalized.
for group1 in groups:
    for group2 in groups:
        if group1 != group2:
            prob += lpSum(y[group1, group2, host] for host in groups) <= 1 + z[3, group1, group2]

status = 0
if "GUROBI_CMD" in availableSolvers:
    print("Solving using Gurobi...     ", end='\r')
    status = prob.solve(GUROBI_CMD(msg=0))
elif "CPLEX_CMD" in availableSolvers:
    print("Solving using CPLEX...     ", end='\r')
    status = prob.solve(CPLEX_CMD(msg=0))
elif "PULP_CBC_CMD" in availableSolvers:
    print("Solving using CBC...     ", end='\r')
    status = prob.solve(PULP_CBC_CMD(msg=0))
else:
    print("Solving using default solver...     ", end='\r')
    status = prob.solve()

print("The problem was solved in {0} seconds.".format(round(perf_counter()-start_perf_counter)))


print("")
for group in groups:
    print(group.name, "has the following schedule:")
    visited_hosts = [host for host in groups if x[group, host].value() > 0.99]
    visited_hosts.sort(key=lambda host: host.host_event_id)
    for e in range(1, len(events)-2):
        travel_from = visited_hosts[e-1]
        travel_to = visited_hosts[e]
        print(" from {0} to {1} in {2} minutes.".format(travel_from.name, travel_to.name, round(travel_times.travel_times[travel_from.location][travel_to.location]/60)))

print("")
print("Guest lists:")
for host in groups:
    guests = [group.name for group in groups if x[group, host].value() > 0.99]
    print(guests, "are at", host.name, "for the", events[host.host_event_id])

print("")
print("Maximum time in between events:")
for e in range(len(events)-1):
    print(round(t[e].value()/60), "Minuten zwischen", events[e], "und", events[e+1])
    
print("")
print("Relaxations:")
print("There are", sum(round(z[1, host].value()) for host in groups), "cases with only 2 groups at one location for an event. That is penalized with", round(p_too_few_cost/60), "minutes each.")
print("There are", sum(round(z[2, host].value()) for host in groups), "cases with 4 groups at one location for an event. That is penalized with", round(p_too_many_cost/60), "minutes each.")
print("There are", sum(round(z[3, group1, group2].value()) for group1 in groups for group2 in groups if group1 != group2), "situations where teams meet more than once. That is penalized with", round(p_too_often_cost/60), "minutes each.")