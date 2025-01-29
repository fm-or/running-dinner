import requests
import json
from typing import List, Tuple, Dict
from pulp import *
from time import perf_counter


def get_coordinates_by_adress(location: str) -> Tuple[float, float]:
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


def get_distances(locations: Dict[str, Tuple[float, float]]) -> Dict[str, Dict[str, float]]:
    measurement = ["distance", "duration"][1]
    transport_mode = ["foot-walking", "cycling-regular", "driving-car"][0]
    location_strings = list(locations.keys())
    body = {"locations": [locations[location_string] for location_string in location_strings],
            "destinations": list(range(len(locations))),
            "metrics": [measurement]}
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': '5b3ce3597851110001cf62484afafd161320478f803cc018ec70f210'
    }
    # start = time.time()
    call = requests.post('https://api.openrouteservice.org/v2/matrix/'+transport_mode, json=body, headers=headers)
    distances = call.json()[measurement+'s']
    return {location_strings[i]: {location_strings[j]: distances[i][j] for j in range(len(location_strings))} for i in range(len(location_strings))}


class Team:

    def __init__(self, name: str, location: str, position: int):
        self.name = name
        self.location = location
        self.position = position

    def __repr__(self):
        return self.name


position_names = ["zu Hause", "Vorspeise", "Hauptspeise", "Nachspeise", "After Party"]

teams = list()
teams.append(Team("Team 1", "Am Schlagbaum 25", 1))
teams.append(Team("Team 2", "Großer Bruch 20", 1))
teams.append(Team("Team 3", "Burgstätter Straße 7", 1))
teams.append(Team("Team 4", "Rollstraße 5", 1))
teams.append(Team("Team 5", "Rollstraße 2", 2))
teams.append(Team("Team 6", "Schulstraße 18a", 2))
teams.append(Team("Team 7", "Adolph-Roemer-Straße 7", 2))
# teams.append(Team("Team 8", "Gerhard-Rauschenbach-Straße 4", 3))
teams.append(Team("Team 8", "Schulstraße 18a", 3))
teams.append(Team("Team 9", "Schulstraße 21", 3))
teams.append(Team("Team 10", "Burgstätter Straße 5", 3))
# teams.append(Team("Team 11", "Rollstraße 2", 3))

after_party = "Erzstraße 45"

p_too_few_cost = 1800
p_too_many_cost = 0
p_too_often_cost = 600

# Sort by position
teams.sort(key=lambda team: team.position)

locations = dict()
for team in teams:
    if team.location not in locations:
        print("Suche nach den Koordinaten von", team.location)
        location_coordinates = get_coordinates_by_adress(team.location)
        locations[team.location] = location_coordinates
locations[after_party] = get_coordinates_by_adress(after_party)  # get_coordinates_by_venue(after_party)
print("Berechne die Zeiten zwischen den Orten")
max_distance = 0
max_pair = None
distances = get_distances(locations)
for location1 in distances.keys():
    for location2 in distances[location1].keys():
        if max_distance < distances[location1][location2]:
            max_distance = distances[location1][location2]
            max_pair = (location1, location2)

print("Maximale Zeit zwischen zwei Teamorten:", round(max_distance/60), "Minuten zwischen", max_pair[0], "und", max_pair[1])

print("")

# check for solvers
availableSolvers = listSolvers(onlyAvailable=True)

v = dict()
for team in teams:
    for team_location in teams:
        for position in [0, 1, 2, 3, 4]:
            v[team, team_location, position] = LpVariable("v[{0},{1},{2}]".format(team, team_location, position), 0, 1, LpBinary)
    v[team, after_party, 4] = LpVariable("v[{0},{1},{2}]".format(team, after_party, 4), 0, 1, LpBinary)
e = dict()
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                e[team, from_location, to_location, from_position] = LpVariable("e[{0},{1},{2},{3}]".format(team, from_location, to_location, from_position), 0, 1, LpBinary)
        e[team, from_location, after_party, 3] = LpVariable("e[{0},{1},{2},{3}]".format(team, from_location, after_party, 3), 0, 1, LpBinary)
t = dict()
for from_position in [0, 1, 2, 3]:
    t[from_position] = LpVariable("t[{0}]".format(from_position), 0, None, LpContinuous) # model.addVar(vtype=GRB.CONTINUOUS, obj=1)
p_too_few = dict()
for team_location in teams:
    for position in [1, 2, 3]:
        p_too_few[team_location, position] = LpVariable("p_too_few[{0},{1}]".format(team_location, position), 0, 1, LpBinary) # model.addVar(vtype=GRB.BINARY, obj=p_too_few_cost)
p_too_many = dict()
for team_location in teams:
    for position in [1, 2, 3]:
        p_too_many[team_location, position] = LpVariable("p_too_many[{0},{1}]".format(team_location, position), 0, 1, LpBinary) # model.addVar(vtype=GRB.BINARY, obj=p_too_many_cost)
p_too_often = dict()
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            p_too_often[team1, team2] = LpVariable("p_too_often[{0},{1}]".format(team1, team2), 0, 1, LpBinary) # model.addVar(vtype=GRB.BINARY, obj=p_too_often_cost)
n = dict()
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            for team_location in teams:
                if team_location not in [team1, team2]:
                    for position in [1, 2, 3]:
                        n[team1, team2, team_location, position] = LpVariable("n[{0},{1},{2},{3}]".format(team1, team2, team_location, position), 0, 1, LpBinary)

start_perf_counter = perf_counter()
prob = LpProblem("RunningPlan", LpMinimize)
prob += lpSum(t[from_position] for from_position in [0, 1, 2, 3]) +\
        + lpSum(p_too_few_cost*p_too_few[team_location, position] for team_location in teams for position in [1, 2, 3]) +\
        + lpSum(p_too_many_cost*p_too_many[team_location, position] for team_location in teams for position in [1, 2, 3]) +\
        + lpSum(p_too_often_cost*p_too_often[team1, team2] for team1 in teams for team2 in teams if team1 != team2)

# if two nodes are visited, the team needs to travel in between
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                prob += v[team, from_location, from_position] + v[team, to_location, from_position+1] <= 1 + e[team, from_location, to_location, from_position]
        prob += v[team, from_location, 3] + v[team, after_party, 4] <= 1 + e[team, from_location, after_party, 3]

# if a team travels between two locations, the team needs to visit them accordingly
'''for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                prob += 2 * e[team, from_location, to_location, from_position] <= v[team, from_location, from_position] + v[team, to_location, from_position+1]
        prob += 2 * e[team, from_location, after_party, 3] <= v[team, from_location, 3] + v[team, after_party, 4]'''

# measure the maximum time from one position to the next
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                prob += e[team, from_location, to_location, from_position] * distances[from_location.location][to_location.location] <= t[from_position]
        prob += e[team, from_location, after_party, 3] * distances[from_location.location][after_party] <= t[3]

# set the home location for the starting position
for team in teams:
    prob += v[team, team, 0] == 1

# set the home location according to the teams position preference
for team in teams:
    prob += v[team, team, team.position] == 1

# set the Querschlag location for the end position
for team in teams:
    prob += v[team, after_party, 4] == 1

# every team needs to be at exactly one location at any given position
for team in teams:
    for position in [0, 1, 2, 3]:
        prob += lpSum(v[team, team_location, position] for team_location in teams) == 1
    prob += lpSum(v[team, team_location, 4] for team_location in teams + [after_party]) == 1

# when a team is at home at a given position, there must be at least two teams, better three
for team_location in teams:
    for position in [1, 2, 3]:
        prob += lpSum(v[team, team_location, position] for team in teams) >= 3 * v[team_location, team_location, position] - p_too_few[team_location, position]

# when a team is not at home at a given position, there can be no other team
for team_location in teams:
    for position in [1, 2, 3]:
        prob += lpSum(v[team, team_location, position] for team in teams) <= 4 * v[team_location, team_location, position]

# check if two teams are at the same place at the same time
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            for team_location in teams:
                if team_location not in [team1, team2]:
                    for position in [1, 2, 3]:
                        prob += v[team1, team_location, position] + v[team2, team_location, position] <= 1 + n[team1, team2, team_location, position]

# check that two teams can only meet once
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            prob += v[team1, team2, team2.position] + v[team2, team1, team1.position] + lpSum(n[team1, team2, team_location, position] for team_location in teams if team_location not in [team1, team2] for position in [1, 2, 3]) <= 1 + p_too_often[team1, team2]

# every team can only visit each team location once
for team in teams:
    for team_location in teams:
        prob += lpSum(v[team, team_location, position] for position in [1, 2, 3]) <= 1

if "GUROBI_CMD" in availableSolvers:
    print("Solving using Gurobi...     ", end='\r')
    prob.solve(GUROBI_CMD(msg=0))
elif "CPLEX_CMD" in availableSolvers:
    print("Solving using CPLEX...     ", end='\r')
    prob.solve(CPLEX_CMD(msg=0))
elif "PULP_CBC_CMD" in availableSolvers:
    print("Solving using CBC...     ", end='\r')
    prob.solve(PULP_CBC_CMD(msg=0))
else:
    print("Solving using default solver...     ", end='\r')
    prob.solve()

print("Das Problem wurde in {0} Sekunden gelöst.".format(round(perf_counter()-start_perf_counter)))

print("")
for team in teams:
    print("Team", team, "hat den folgenden Ablauf:")
    last_location = after_party
    for position in [1, 2, 3]:
        for team_location in teams:
            if v[team, team_location, position].value() > 0.99:
                print(" in", round(distances[last_location][team_location.location]/60), "Minuten zu", team_location.location, "bei Team", team_location.name)
                last_location = team_location.location
    for team_location in teams + [after_party]:
        if v[team, team_location, 4].value() > 0.99:
            location = team_location if isinstance(team_location, str) else team_location.location
            print(" in", round(distances[last_location][location]/60), "Minuten zu", location)

print("")
print("Gäste der Teams:")
for team in teams:
    guests = [guest_team for guest_team in teams if v[guest_team, team, team.position].value() > 0.99]
    print(guests, "sind bei", team, "für die", position_names[team.position])

print("")
print("Maximale Zeit zwischen zwei Gerichten:")
for from_position in [0, 1, 2, 3]:
    print(round(t[from_position].value()/60), "Minuten zwischen", position_names[from_position], "und", position_names[from_position+1])

print("")
print("Ausnahmen:")
print(sum(round(p_too_few[team_location, position].value()) for team_location in teams for position in [1, 2, 3]), "Gerichte mit zu wenig Teams. Das wird mit je", round(p_too_few_cost/60), "Minuten bestraft.")
# print(sum(round(p_too_many[team_location, position].value()) for team_location in teams for position in [1, 2, 3]), "Fälle mit zu vielen Teams. Je", round(p_too_many_cost/60), "Minuten extra.")
print(sum(round(p_too_often[team1, team2].value()) for team1 in teams for team2 in teams if team1 != team2), "Situationen in denen ein Team ein anderes mehrfach trifft. Das wird mit je", round(p_too_often_cost/60), "Minuten bestraft.")
