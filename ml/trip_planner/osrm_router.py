from pathlib import Path
import json
import requests
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"

OSRM_BASE_URL = "https://router.project-osrm.org"


def get_osrm_route(points):

    if len(points) < 2:
        return None

    coordinates = ";".join(
        f"{point['longitude']},{point['latitude']}"
        for point in points
    )

    url = (
        f"{OSRM_BASE_URL}"
        f"/route/v1/driving/"
        f"{coordinates}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        raise ValueError(
            f"OSRM error: {data}"
        )

    route = data["routes"][0]

    return {
        "distance_km":
            round(
                route["distance"] / 1000,
                2
            ),

        "duration_minutes":
            round(
                route["duration"] / 60,
                1
            ),

        "geometry":
            route["geometry"]
    }


def build_daily_osrm_routes(itinerary):

    results = []

    for day in sorted(
        itinerary["day"].unique()
    ):

        day_data = (
            itinerary[
                itinerary["day"] == day
            ]
            .copy()
        )

        points = []

        for _, row in day_data.iterrows():

            if (
                pd.isna(row["latitude"])
                or
                pd.isna(row["longitude"])
            ):
                continue

            points.append({
                "name":
                    row["name"],

                "type":
                    row["type"],

                "latitude":
                    float(row["latitude"]),

                "longitude":
                    float(row["longitude"])
            })

        route = get_osrm_route(
            points
        )

        if route is None:
            continue

        results.append({

            "day":
                int(day),

            "stops":
                points,

            "distance_km":
                route["distance_km"],

            "duration_minutes":
                route["duration_minutes"],

            "geometry":
                route["geometry"]
        })

    return results


if __name__ == "__main__":

    itinerary = pd.read_csv(
        PROCESSED_DIR
        / "waxn_optimized_itinerary.csv"
    )

    routes = build_daily_osrm_routes(
        itinerary
    )

    print("=" * 70)
    print("WAXN AI OSRM ROAD ROUTING")
    print("=" * 70)

    for route in routes:

        print(
            f"\nDAY {route['day']}"
        )

        print(
            "Road distance:",
            route["distance_km"],
            "km"
        )

        print(
            "Estimated driving:",
            route["duration_minutes"],
            "minutes"
        )

        print("Stops:")

        for stop in route["stops"]:

            print(
                f" - {stop['type'].upper():12}"
                f" {stop['name']}"
            )

    output = (
        PROCESSED_DIR
        / "waxn_osrm_routes.json"
    )

    with open(
        output,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            routes,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nSaved:",
        output
    )

    print("=" * 70)