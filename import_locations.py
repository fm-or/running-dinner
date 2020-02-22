import requests
import json
from typing import List, Tuple, Dict
from gurobipy import GRB, Model, quicksum


def get_coordinates_by_adress(location: str) -> Tuple[float, float]:
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8'
    }
    authorization = '5b3ce3597851110001cf6248d990de15874844ddac1347c5541fbcdd'
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
    authorization = '5b3ce3597851110001cf6248d990de15874844ddac1347c5541fbcdd'
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
        'Authorization': '5b3ce3597851110001cf6248d990de15874844ddac1347c5541fbcdd'
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
teams.append(Team("LuzieLuanaFranzi", "Am Schlagbaum 25", 1))
teams.append(Team("JanChristina", "Großer Bruch 20", 1))
teams.append(Team("MoritzAlex", "Burgstätter Straße 7", 1))
teams.append(Team("AnnikaChristian", "Rollstraße 5", 1))
teams.append(Team("SouzHenry", "Rollstraße 2", 2))
teams.append(Team("LenaXX", "Schulstraße 18a", 2))
teams.append(Team("MarcScarlett", "Adolph-Roemer-Straße 7", 2))
# teams.append(Team("AstridTheresa", "Gerhard-Rauschenbach-Straße 4", 3))
teams.append(Team("AstridTheresa", "Schulstraße 18a", 3))
# teams.append(Team("HannesLara", "Rollstraße 2", 3))
teams.append(Team("LauraChris", "Schulstraße 21", 3))
teams.append(Team("GretaTill", "Burgstätter Straße 5", 3))

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

model = Model()
model.setParam("outputFlag", False)
v = dict()
for team in teams:
    for team_location in teams:
        for position in [0, 1, 2, 3, 4]:
            v[team, team_location, position] = model.addVar(vtype=GRB.BINARY)
    v[team, after_party, 4] = model.addVar(vtype=GRB.BINARY)
e = dict()
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                e[team, from_location, to_location, from_position] = model.addVar(vtype=GRB.BINARY)
        e[team, from_location, after_party, 3] = model.addVar(vtype=GRB.BINARY)
t = dict()
for from_position in [0, 1, 2, 3]:
    t[from_position] = model.addVar(vtype=GRB.CONTINUOUS, obj=1)
p_too_few = dict()
for team_location in teams:
    for position in [1, 2, 3]:
        p_too_few[team_location, position] = model.addVar(vtype=GRB.BINARY, obj=p_too_few_cost)
p_too_many = dict()
for team_location in teams:
    for position in [1, 2, 3]:
        p_too_many[team_location, position] = model.addVar(vtype=GRB.BINARY, obj=p_too_many_cost)
p_too_often = dict()
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            p_too_often[team1, team2] = model.addVar(vtype=GRB.BINARY, obj=p_too_often_cost)
n = dict()
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            for team_location in teams:
                if team_location not in [team1, team2]:
                    for position in [1, 2, 3]:
                        n[team1, team2, team_location, position] = model.addVar(vtype=GRB.BINARY)
model.update()

# if two nodes are visited, the team needs to travel in between
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                model.addConstr(v[team, from_location, from_position] + v[team, to_location, from_position+1] <= 1 + e[team, from_location, to_location, from_position])
        model.addConstr(v[team, from_location, 3] + v[team, after_party, 4] <= 1 + e[team, from_location, after_party, 3])

# if a team travels between two locations, the team needs to visit them accordingly
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                model.addConstr(2 * e[team, from_location, to_location, from_position] <= v[team, from_location, from_position] + v[team, to_location, from_position+1])
        model.addConstr(2 * e[team, from_location, after_party, 3] <= v[team, from_location, 3] + v[team, after_party, 4])

# measure the maximum time from one position to the next
for team in teams:
    for from_location in teams:
        for to_location in teams:
            for from_position in [0, 1, 2, 3]:
                model.addConstr(e[team, from_location, to_location, from_position] * distances[from_location.location][to_location.location] <= t[from_position])
        model.addConstr(e[team, from_location, after_party, 3] * distances[from_location.location][after_party] <= t[3])

# set the home location for the starting position
for team in teams:
    model.addConstr(v[team, team, 0] == 1)

# set the home location according to the teams position preference
for team in teams:
    model.addConstr(v[team, team, team.position] == 1)

# set the Querschlag location for the end position
for team in teams:
    model.addConstr(v[team, after_party, 4] == 1)

# every team needs to be at exactly one location at any given position
for team in teams:
    for position in [0, 1, 2, 3]:
        model.addConstr(quicksum(v[team, team_location, position] for team_location in teams) == 1)
    model.addConstr(quicksum(v[team, team_location, 4] for team_location in teams + [after_party]) == 1)

# when a team is at home at a given position, there must be at least two teams, better three
for team_location in teams:
    for position in [1, 2, 3]:
        model.addConstr(quicksum(v[team, team_location, position] for team in teams) >= 3 * v[team_location, team_location, position] - p_too_few[team_location, position])

# when a team is not at home at a given position, there can be no other team
for team_location in teams:
    for position in [1, 2, 3]:
        model.addConstr(quicksum(v[team, team_location, position] for team in teams) <= 4 * v[team_location, team_location, position])

# check if two teams are at the same place at the same time
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            for team_location in teams:
                if team_location not in [team1, team2]:
                    for position in [1, 2, 3]:
                        model.addConstr(v[team1, team_location, position] + v[team2, team_location, position] <= 1 + n[team1, team2, team_location, position])

# check that two teams can only meet once
for team1 in teams:
    for team2 in teams:
        if team1 != team2:
            model.addConstr(v[team1, team2, team2.position] + v[team2, team1, team1.position] + quicksum(n[team1, team2, team_location, position] for team_location in teams if team_location not in [team1, team2] for position in [1, 2, 3]) <= 1 + p_too_often[team1, team2])

# every team can only visit each team once
for team in teams:
    for team_location in teams:
        model.addConstr(quicksum(v[team, team_location, position] for position in [1, 2, 3]) <= 1)

model.optimize()

print("")
for team in teams:
    print("Team", team, "hat den folgenden Ablauf:")
    last_location = after_party
    for position in [1, 2, 3]:
        for team_location in teams:
            if v[team, team_location, position].X > 0.99:
                print(" in", round(distances[last_location][team_location.location]/60), "Minuten zu", team_location.location, "bei Team", team_location.name)
                last_location = team_location.location
    for team_location in teams + [after_party]:
        if v[team, team_location, 4].X > 0.99:
            location = team_location if isinstance(team_location, str) else team_location.location
            print(" in", round(distances[last_location][location]/60), "Minuten zu", location)

print("")
print("Gäste der Teams:")
for team in teams:
    guests = [guest_team for guest_team in teams if v[guest_team, team, team.position].X > 0.99]
    print(guests, "sind bei", team, "für die", position_names[team.position])

print("")
print("Maximale Zeit zwischen zwei Gerichten:")
for from_position in [0, 1, 2, 3]:
    print(round(t[from_position].X/60), "Minuten zwischen", position_names[from_position], "und", position_names[from_position+1])

print("")
print("Ausnahmen:")
print(sum(round(p_too_few[team_location, position].X) for team_location in teams for position in [1, 2, 3]), "Gerichte mit zu wenig Teams. Das wird mit je", round(p_too_few_cost/60), "Minuten bestraft.")
# print(sum(round(p_too_many[team_location, position].X) for team_location in teams for position in [1, 2, 3]), "Fälle mit zu vielen Teams. Je", round(p_too_many_cost/60), "Minuten extra.")
print(sum(round(p_too_often[team1, team2].X) for team1 in teams for team2 in teams if team1 != team2), "Situationen in denen ein Team ein anderes mehrfach trifft. Das wird mit je", round(p_too_often_cost/60), "Minuten bestraft.")
