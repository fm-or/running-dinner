from model.DinnerInstance import DinnerInstance


print("Getting locations and distances...")
instance = DinnerInstance(
    ors_auth_key = "your-ors-key",
    country_code = "DE",
    city_address= "33602 Bielefeld",
    events = ["zu Hause", "Vorspeise", "Hauptspeise", "Nachspeise", "After Party"],
    addresses = [
        ("Group 1", "Niederwall 23", 1),
        ("Group 2", "August-Bebel-Straße 94", 1),
        ("Group 3", "Ravensberger Straße 12", 1),
        ("Group 4", "Turnerstraße 5", 1),
        ("Group 5", "Wilhelmstraße 3", 2),
        ("Group 6", "Kavalleriestraße 17", 2),
        ("Group 7", "Feilenstraße 31", 2),
        ("Group 8", "Paulusstraße 19", 3),
        ("Group 9", "Detmolder Straße 1", 3),
        ("Group 10", "Elsa-Brändström-Strasse 12", 3)
    ],
party_address="Jahnplatz")

print("Solving...")
solution = instance.solve(
    penalty_too_few_guests = 1800,
    penalty_too_many_guests = 0,
    penalty_multiple_encounters = 600,
    prioritized_solver_str = "GUROBI_CMD") # e.g. GLPK_CMD, CPLEX_CMD, GUROBI_CMD, PULP_CBC_CMD

print("Saving csv...")
instance.save_csv("example-solution.csv", solution)

print("Drawing map...")
instance.save_map("example-map.html", solution)
