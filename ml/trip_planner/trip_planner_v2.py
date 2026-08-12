from pathlib import Path
import sys

import pandas as pd
from sklearn.cluster import KMeans

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from ml.recommendation.dynamic_recommender import (
    recommend_attractions,
    recommend_food,
    recommend_hotels,
)


PROCESSED_DIR = BASE_DIR / "data" / "processed"


def cluster_places(attractions, days):
    attractions = attractions.copy()

    attractions = attractions[
        attractions["latitude"].notna()
        & attractions["longitude"].notna()
    ].copy()

    if len(attractions) <= days:
        attractions["day_cluster"] = range(
            1,
            len(attractions) + 1
        )
        return attractions

    coords = attractions[
        ["latitude", "longitude"]
    ].values

    model = KMeans(
        n_clusters=days,
        random_state=42,
        n_init=20
    )

    attractions["day_cluster"] = (
        model.fit_predict(coords) + 1
    )

    return attractions


def nearest_place(target_lat, target_lon, candidates):
    if candidates.empty:
        return None

    data = candidates.copy()

    data["distance_score"] = (
        (data["latitude"] - target_lat) ** 2
        +
        (data["longitude"] - target_lon) ** 2
    )

    return data.sort_values(
        "distance_score"
    ).iloc[0]


def plan_trip_v2(
    district,
    days=3,
    nature=0.5,
    adventure=0.5,
    history=0.5,
    photography=0.5,
    food=0.5,
    relaxation=0.5,
    family=0.5,
    shopping=0.5,
):

    preferences = {
        "nature": nature,
        "adventure": adventure,
        "history": history,
        "photography": photography,
        "food": food,
        "relaxation": relaxation,
        "family": family,
        "shopping": shopping,
    }

    attractions = recommend_attractions(
        district=district,
        top_n=days * 5,
        **preferences
    )

    restaurants = recommend_food(
        district=district,
        top_n=30,
        **preferences
    )

    hotels = recommend_hotels(
        district=district,
        top_n=20,
        **preferences
    )

    if attractions.empty:
        raise ValueError(
            f"No attractions found for {district}"
        )

    clustered = cluster_places(
        attractions,
        days
    )

    # Pick one strong hotel near overall attraction center
    center_lat = clustered["latitude"].mean()
    center_lon = clustered["longitude"].mean()

    selected_hotel = nearest_place(
        center_lat,
        center_lon,
        hotels
    )

    itinerary_rows = []

    for day in range(1, days + 1):

        day_places = clustered[
            clustered["day_cluster"] == day
        ].copy()

        # Keep max 3 attractions per day
        day_places = (
            day_places
            .sort_values(
                "recommendation_score",
                ascending=False
            )
            .head(3)
        )

        if day_places.empty:
            continue

        day_center_lat = day_places[
            "latitude"
        ].mean()

        day_center_lon = day_places[
            "longitude"
        ].mean()

        selected_food = nearest_place(
            day_center_lat,
            day_center_lon,
            restaurants
        )

        times = [
            "09:00",
            "11:30",
            "15:30"
        ]

        for position, (_, row) in enumerate(
            day_places.iterrows()
        ):

            itinerary_rows.append({
                "day": day,
                "time": times[position],
                "type": "attraction",
                "place_id": row["place_id"],
                "name": row["name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
            })

        if selected_food is not None:

            itinerary_rows.append({
                "day": day,
                "time": "13:30",
                "type": "food",
                "place_id": selected_food["place_id"],
                "name": selected_food["name"],
                "latitude": selected_food["latitude"],
                "longitude": selected_food["longitude"],
            })

        if selected_hotel is not None:

            itinerary_rows.append({
                "day": day,
                "time": "19:00",
                "type": "hotel",
                "place_id": selected_hotel["place_id"],
                "name": selected_hotel["name"],
                "latitude": selected_hotel["latitude"],
                "longitude": selected_hotel["longitude"],
            })

    return pd.DataFrame(itinerary_rows)


if __name__ == "__main__":

    itinerary = plan_trip_v2(
        district="Badulla",
        days=3,

        nature=0.9,
        adventure=0.8,
        history=0.3,
        photography=1.0,
        food=0.7,
        relaxation=0.5,
        family=0.2,
        shopping=0.1,
    )

    print("=" * 70)
    print("WAXN AI TRIP PLANNER V2")
    print("=" * 70)

    for day in sorted(
        itinerary["day"].unique()
    ):

        print(f"\nDAY {day}")
        print("-" * 70)

        day_data = itinerary[
            itinerary["day"] == day
        ]

        for _, row in day_data.iterrows():

            print(
                f'{row["time"]} '
                f'{row["type"].upper():12} '
                f'{row["name"]}'
            )

    output = (
        PROCESSED_DIR
        / "waxn_test_itinerary_v2.csv"
    )

    itinerary.to_csv(
        output,
        index=False
    )

    print("\nSaved:")
    print(output)