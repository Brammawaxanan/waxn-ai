from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# DISTANCE FUNCTION
# ============================================================

def haversine_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    R = 6371.0

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

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

    return R * c


# ============================================================
# NEAREST-NEIGHBOR ROUTE
# ============================================================

def optimize_day_route(day_df):

    day_df = day_df.copy()

    hotel_rows = day_df[
        day_df["type"] == "hotel"
    ]

    if hotel_rows.empty:
        return day_df

    hotel = hotel_rows.iloc[0]

    current_lat = hotel["latitude"]
    current_lon = hotel["longitude"]

    movable = day_df[
        day_df["type"] != "hotel"
    ].copy()

    ordered_rows = []

    while not movable.empty:

        distances = []

        for index, row in movable.iterrows():

            distance = haversine_distance(
                current_lat,
                current_lon,
                row["latitude"],
                row["longitude"]
            )

            distances.append(
                (
                    index,
                    distance
                )
            )

        nearest_index, nearest_distance = min(
            distances,
            key=lambda x: x[1]
        )

        nearest_row = movable.loc[
            nearest_index
        ].copy()

        nearest_row[
            "distance_from_previous_km"
        ] = round(
            nearest_distance,
            2
        )

        ordered_rows.append(
            nearest_row
        )

        current_lat = nearest_row[
            "latitude"
        ]

        current_lon = nearest_row[
            "longitude"
        ]

        movable = movable.drop(
            nearest_index
        )

    # Return to hotel
    hotel_copy = hotel.copy()

    return_distance = haversine_distance(
        current_lat,
        current_lon,
        hotel["latitude"],
        hotel["longitude"]
    )

    hotel_copy[
        "distance_from_previous_km"
    ] = round(
        return_distance,
        2
    )

    ordered_rows.append(
        hotel_copy
    )

    result = pd.DataFrame(
        ordered_rows
    )

    return result


# ============================================================
# FULL TRIP OPTIMIZATION
# ============================================================

def optimize_trip(itinerary):

    optimized_days = []

    for day in sorted(
        itinerary["day"].unique()
    ):

        day_df = itinerary[
            itinerary["day"] == day
        ].copy()

        optimized_day = optimize_day_route(
            day_df
        )

        optimized_day[
            "day"
        ] = day

        optimized_days.append(
            optimized_day
        )

    result = pd.concat(
        optimized_days,
        ignore_index=True
    )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    itinerary = pd.read_csv(
        PROCESSED_DIR
        / "waxn_test_itinerary.csv"
    )

    optimized = optimize_trip(
        itinerary
    )

    print("=" * 70)
    print("WAXN AI ROUTE OPTIMIZER")
    print("=" * 70)

    for day in sorted(
        optimized["day"].unique()
    ):

        print(
            f"\nDAY {day}"
        )

        print(
            "-" * 70
        )

        day_plan = optimized[
            optimized["day"] == day
        ]

        total_distance = 0

        for _, row in day_plan.iterrows():

            distance = row.get(
                "distance_from_previous_km",
                0
            )

            total_distance += (
                0
                if pd.isna(distance)
                else distance
            )

            print(
                f'{row["type"].upper():12}  '
                f'{row["name"]:<40} '
                f'{distance:.2f} km'
            )

        print(
            f"Total estimated distance: "
            f"{total_distance:.2f} km"
        )

    optimized.to_csv(
        PROCESSED_DIR
        / "waxn_optimized_itinerary.csv",
        index=False
    )

    print("\nSaved:")
    print(
        "data/processed/waxn_optimized_itinerary.csv"
    )

    print("=" * 70)