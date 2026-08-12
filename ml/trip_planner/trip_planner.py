from pathlib import Path
import sys
import pandas as pd


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

sys.path.append(str(BASE_DIR))

from ml.recommendation.dynamic_recommender import (
    recommend_attractions,
    recommend_food,
    recommend_hotels,
)


# ============================================================
# HELPER
# ============================================================

def build_daily_schedule(day_number, attractions, food, hotel):

    schedule = []

    # Morning attraction
    if len(attractions) > 0:

        schedule.append({
            "day": day_number,
            "time": "09:00",
            "type": "attraction",
            "place_id": attractions.iloc[0]["place_id"],
            "name": attractions.iloc[0]["name"],
            "latitude": attractions.iloc[0]["latitude"],
            "longitude": attractions.iloc[0]["longitude"],
        })


    # Second attraction
    if len(attractions) > 1:

        schedule.append({
            "day": day_number,
            "time": "11:30",
            "type": "attraction",
            "place_id": attractions.iloc[1]["place_id"],
            "name": attractions.iloc[1]["name"],
            "latitude": attractions.iloc[1]["latitude"],
            "longitude": attractions.iloc[1]["longitude"],
        })


    # Lunch
    if food is not None:

        schedule.append({
            "day": day_number,
            "time": "13:30",
            "type": "food",
            "place_id": food["place_id"],
            "name": food["name"],
            "latitude": food["latitude"],
            "longitude": food["longitude"],
        })


    # Afternoon attraction
    if len(attractions) > 2:

        schedule.append({
            "day": day_number,
            "time": "15:30",
            "type": "attraction",
            "place_id": attractions.iloc[2]["place_id"],
            "name": attractions.iloc[2]["name"],
            "latitude": attractions.iloc[2]["latitude"],
            "longitude": attractions.iloc[2]["longitude"],
        })


    # Hotel
    if hotel is not None:

        schedule.append({
            "day": day_number,
            "time": "19:00",
            "type": "hotel",
            "place_id": hotel["place_id"],
            "name": hotel["name"],
            "latitude": hotel["latitude"],
            "longitude": hotel["longitude"],
        })


    return schedule


# ============================================================
# MAIN TRIP PLANNER
# ============================================================

def plan_trip(
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

    print("=" * 70)
    print("WAXN AI TRIP PLANNER")
    print("=" * 70)

    print("District:", district)
    print("Days:", days)


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


    # --------------------------------------------------------
    # Calculate required recommendations
    # --------------------------------------------------------

    attractions_needed = days * 3

    food_needed = days

    hotels_needed = max(
        days,
        5
    )


    # --------------------------------------------------------
    # Get recommendations
    # --------------------------------------------------------

    attractions = recommend_attractions(
        district=district,
        top_n=attractions_needed,
        **preferences
    )


    restaurants = recommend_food(
        district=district,
        top_n=food_needed,
        **preferences
    )


    hotels = recommend_hotels(
        district=district,
        top_n=hotels_needed,
        **preferences
    )


    print(
        "\nRecommended attractions:",
        len(attractions)
    )

    print(
        "Recommended restaurants:",
        len(restaurants)
    )

    print(
        "Recommended hotels:",
        len(hotels)
    )


    if attractions.empty:

        raise ValueError(
            f"No attractions found for {district}"
        )


    # --------------------------------------------------------
    # Select one hotel for the whole trip
    # --------------------------------------------------------

    selected_hotel = None

    if not hotels.empty:

        selected_hotel = hotels.iloc[0]


    # --------------------------------------------------------
    # Build itinerary
    # --------------------------------------------------------

    complete_schedule = []


    for day in range(
        1,
        days + 1
    ):

        start_index = (
            (day - 1) * 3
        )

        end_index = (
            start_index + 3
        )


        day_attractions = (
            attractions
            .iloc[
                start_index:end_index
            ]
        )


        day_food = None

        if len(restaurants) >= day:

            day_food = (
                restaurants
                .iloc[
                    day - 1
                ]
            )


        day_schedule = build_daily_schedule(

            day_number=day,

            attractions=day_attractions,

            food=day_food,

            hotel=selected_hotel,
        )


        complete_schedule.extend(
            day_schedule
        )


    itinerary = pd.DataFrame(
        complete_schedule
    )


    return {
        "district":
            district,

        "days":
            days,

        "hotel":
            (
                selected_hotel.to_dict()
                if selected_hotel is not None
                else None
            ),

        "attractions":
            attractions,

        "restaurants":
            restaurants,

        "itinerary":
            itinerary,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    trip = plan_trip(

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


    itinerary = trip[
        "itinerary"
    ]


    print(
        "\n"
        "=" * 70
    )

    print(
        "GENERATED ITINERARY"
    )

    print(
        "=" * 70
    )


    for day in sorted(
        itinerary["day"].unique()
    ):

        print(
            f"\nDAY {day}"
        )

        print(
            "-" * 70
        )


        day_plan = itinerary[
            itinerary["day"]
            ==
            day
        ]


        for _, row in day_plan.iterrows():

            print(

                f'{row["time"]}  '

                f'{row["type"].upper():12}  '

                f'{row["name"]}'
            )


    # --------------------------------------------------------
    # Save test itinerary
    # --------------------------------------------------------

    OUTPUT_DIR = (
        BASE_DIR
        / "data"
        / "processed"
    )


    itinerary.to_csv(

        OUTPUT_DIR
        / "waxn_test_itinerary.csv",

        index=False
    )


    print(
        "\nSaved:"
    )

    print(
        "data/processed/waxn_test_itinerary.csv"
    )


    print(
        "=" * 70
    )

    print(
        "TRIP PLANNER V1 COMPLETE"
    )

    print(
        "=" * 70
    )

    