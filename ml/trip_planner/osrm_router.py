from pathlib import Path
import json
from math import atan2, cos, radians, sin, sqrt
import requests
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"

OSRM_BASE_URL = "https://router.project-osrm.org"
FALLBACK_ROAD_DISTANCE_MULTIPLIER = 1.3
FALLBACK_AVERAGE_SPEED_KMPH = 35


def haversine_distance(
    point_a,
    point_b
):
    radius_km = 6371.0

    lat1 = radians(point_a["latitude"])
    lon1 = radians(point_a["longitude"])
    lat2 = radians(point_b["latitude"])
    lon2 = radians(point_b["longitude"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        *
        cos(lat2)
        *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return radius_km * c


def build_fallback_route(points):
    distance_km = 0

    for index in range(
        1,
        len(points)
    ):

        distance_km += haversine_distance(
            points[index - 1],
            points[index]
        )

    distance_km *= FALLBACK_ROAD_DISTANCE_MULTIPLIER

    duration_minutes = (
        distance_km
        /
        FALLBACK_AVERAGE_SPEED_KMPH
        *
        60
    )

    return {
        "distance_km":
            round(
                distance_km,
                2
            ),

        "duration_minutes":
            round(
                duration_minutes,
                1
            ),

        "geometry": {
            "type": "LineString",
            "coordinates": [
                [
                    point["longitude"],
                    point["latitude"]
                ]
                for point in points
            ]
        },

        "routing_source":
            "haversine_fallback"
    }


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

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as error:

        print(
            "OSRM request failed; using fallback route:",
            type(error).__name__
        )

        return build_fallback_route(
            points
        )

    except ValueError as error:

        print(
            "OSRM response was not valid JSON; using fallback route:",
            type(error).__name__
        )

        return build_fallback_route(
            points
        )

    if data.get("code") != "Ok":

        print(
            "OSRM returned error; using fallback route:",
            data.get("code")
        )

        return build_fallback_route(
            points
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
            route["geometry"],

        "routing_source":
            "osrm"
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
                route["geometry"],

            "routing_source":
                route["routing_source"]
        })

    return results


if __name__ == "__main__":

    itinerary = pd.read_csv(
        PROCESSED_DIR
        / "waxn_constrained_itinerary.csv"
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

        print(
            "Routing source:",
            route["routing_source"]
        )

        print("Stops:")

        for stop in route["stops"]:

            print(
                f" - {stop['type'].upper():12}"
                f" {stop['name']}"
            )

    output = (
        PROCESSED_DIR
        / "waxn_final_routes.json"
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
