from pathlib import Path
import json
from math import radians, sin, cos, sqrt, atan2

import pandas as pd
import requests


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"

CANDIDATE_FILE = (
    PROCESSED_DIR
    / "waxn_recommendation_candidates.csv"
)

ITINERARY_FILE = (
    PROCESSED_DIR
    / "waxn_optimized_itinerary.csv"
)

OSRM_BASE_URL = "https://router.project-osrm.org"


# ============================================================
# DAILY LIMITS
# ============================================================

MAX_DAILY_DISTANCE_KM = 70
MAX_DAILY_DURATION_MIN = 150

MAX_REPLAN_ATTEMPTS = 5


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine(
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
# OSRM ROUTE METRICS
# ============================================================

def get_route_metrics(day_df):

    points = []

    for _, row in day_df.iterrows():

        if (
            pd.isna(row.get("latitude"))
            or
            pd.isna(row.get("longitude"))
        ):
            continue

        points.append(
            (
                float(row["longitude"]),
                float(row["latitude"])
            )
        )

    if len(points) < 2:
        return None

    coordinates = ";".join(
        f"{lon},{lat}"
        for lon, lat in points
    )

    url = (
        f"{OSRM_BASE_URL}"
        f"/route/v1/driving/"
        f"{coordinates}"
    )

    try:

        response = requests.get(
            url,
            params={
                "overview": "false"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as error:

        print(
            "OSRM request failed:",
            error
        )

        return None


    if data.get("code") != "Ok":

        print(
            "OSRM returned error:",
            data
        )

        return None


    route = data["routes"][0]

    return {

        "distance_km":
            route["distance"] / 1000,

        "duration_minutes":
            route["duration"] / 60,
    }


# ============================================================
# VALID CANDIDATES
# ============================================================

def prepare_candidates(candidates):

    candidates = candidates.copy()

    candidates = candidates[
        candidates["category"].isin(
            [
                "attraction",
                "activity"
            ]
        )
    ].copy()

    candidates = candidates[
        candidates["latitude"].notna()
        &
        candidates["longitude"].notna()
    ].copy()


    if "quality_score" not in candidates.columns:

        candidates[
            "quality_score"
        ] = 0.0


    if "data_quality_score" not in candidates.columns:

        candidates[
            "data_quality_score"
        ] = 0.0


    candidates[
        "quality_score"
    ] = (
        pd.to_numeric(
            candidates[
                "quality_score"
            ],
            errors="coerce"
        )
        .fillna(0)
    )


    candidates[
        "data_quality_score"
    ] = (
        pd.to_numeric(
            candidates[
                "data_quality_score"
            ],
            errors="coerce"
        )
        .fillna(0)
    )


    return candidates


# ============================================================
# FIND DAY CENTER
# ============================================================

def get_day_center(day_df):

    valid = day_df[
        day_df["latitude"].notna()
        &
        day_df["longitude"].notna()
    ]

    if valid.empty:
        return None, None

    return (
        valid["latitude"].mean(),
        valid["longitude"].mean()
    )


# ============================================================
# FIND REPLACEMENT
# ============================================================

def find_replacement(
    removed_row,
    day_df,
    candidates,
    used_place_ids
):

    attraction_candidates = (
        prepare_candidates(
            candidates
        )
    )


    # --------------------------------------------------------
    # Remove already used places
    # --------------------------------------------------------

    attraction_candidates = (
        attraction_candidates[
            ~attraction_candidates[
                "place_id"
            ]
            .astype(str)
            .isin(
                used_place_ids
            )
        ]
        .copy()
    )


    if attraction_candidates.empty:
        return None


    # --------------------------------------------------------
    # District preference
    # --------------------------------------------------------

    removed_district = str(
        removed_row.get(
            "district",
            ""
        )
    ).strip().lower()


    if removed_district:

        same_district = (
            attraction_candidates[
                attraction_candidates[
                    "district"
                ]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.strip()
                .eq(
                    removed_district
                )
            ]
        )

        if not same_district.empty:

            attraction_candidates = (
                same_district.copy()
            )


    # --------------------------------------------------------
    # Day center
    # --------------------------------------------------------

    center_lat, center_lon = (
        get_day_center(
            day_df
        )
    )


    if (
        center_lat is None
        or
        center_lon is None
    ):
        return None


    # --------------------------------------------------------
    # Distance from current day cluster
    # --------------------------------------------------------

    attraction_candidates[
        "nearby_distance"
    ] = (
        attraction_candidates.apply(

            lambda row:

            haversine(
                center_lat,
                center_lon,
                row["latitude"],
                row["longitude"]
            ),

            axis=1
        )
    )


    # --------------------------------------------------------
    # Optional hard nearby limit
    # --------------------------------------------------------

    nearby = (
        attraction_candidates[
            attraction_candidates[
                "nearby_distance"
            ] <= 25
        ]
        .copy()
    )


    if not nearby.empty:

        attraction_candidates = (
            nearby
        )


    # --------------------------------------------------------
    # Replacement score
    # --------------------------------------------------------

    attraction_candidates[
        "replacement_score"
    ] = (

        attraction_candidates[
            "quality_score"
        ] * 0.50

        +

        attraction_candidates[
            "data_quality_score"
        ] * 0.30

        +

        (
            1
            -
            (
                attraction_candidates[
                    "nearby_distance"
                ]
                .clip(
                    upper=100
                )
                /
                100
            )
        ) * 0.20
    )


    # --------------------------------------------------------
    # Avoid weak/generic candidate names
    # --------------------------------------------------------

    weak_phrases = [
        "viewpoint rock",
        "free entry",
        "via steps",
        "railway trek",
        "unnamed",
        "unknown"
    ]


    def weak_name(name):

        text = str(
            name
        ).lower()

        return any(
            phrase in text
            for phrase in weak_phrases
        )


    attraction_candidates[
        "weak_name"
    ] = (
        attraction_candidates[
            "name"
        ].apply(
            weak_name
        )
    )


    good_candidates = (
        attraction_candidates[
            ~attraction_candidates[
                "weak_name"
            ]
        ]
    )


    if not good_candidates.empty:

        attraction_candidates = (
            good_candidates
        )


    # --------------------------------------------------------
    # Pick best replacement
    # --------------------------------------------------------

    best = (
        attraction_candidates

        .sort_values(
            [
                "replacement_score",
                "quality_score",
                "data_quality_score"
            ],
            ascending=[
                False,
                False,
                False
            ]
        )

        .iloc[0]
    )


    return best


# ============================================================
# FIND FURTHEST ATTRACTION
# ============================================================

def find_furthest_attraction(
    day_df
):

    attractions = (
        day_df[
            day_df["type"]
            ==
            "attraction"
        ]
        .copy()
    )


    if attractions.empty:
        return None


    center_lat, center_lon = (
        get_day_center(
            day_df
        )
    )


    if (
        center_lat is None
        or
        center_lon is None
    ):
        return None


    attractions[
        "distance_from_center"
    ] = (
        attractions.apply(

            lambda row:

            haversine(
                center_lat,
                center_lon,
                row["latitude"],
                row["longitude"]
            ),

            axis=1
        )
    )


    return (
        attractions[
            "distance_from_center"
        ]
        .idxmax()
    )


# ============================================================
# UPDATE REPLACEMENT
# ============================================================

def apply_replacement(
    day_df,
    row_index,
    replacement
):

    fields = [
        "place_id",
        "name",
        "latitude",
        "longitude"
    ]


    for field in fields:

        if field in replacement.index:

            day_df.at[
                row_index,
                field
            ] = replacement[
                field
            ]


    return day_df


# ============================================================
# REPLAN SINGLE DAY
# ============================================================

def replan_day(
    day_df,
    candidates,
    used_place_ids
):

    day_df = (
        day_df.copy()
        .reset_index(
            drop=True
        )
    )


    metrics = (
        get_route_metrics(
            day_df
        )
    )


    if metrics is None:

        return day_df, None


    print(
        f"Initial: "
        f"{metrics['distance_km']:.2f} km / "
        f"{metrics['duration_minutes']:.1f} min"
    )


    attempts = 0


    while (

        (
            metrics[
                "distance_km"
            ]
            >
            MAX_DAILY_DISTANCE_KM

            or

            metrics[
                "duration_minutes"
            ]
            >
            MAX_DAILY_DURATION_MIN
        )

        and

        attempts
        <
        MAX_REPLAN_ATTEMPTS
    ):

        attempts += 1


        print(
            f"\nReplan attempt {attempts}"
        )


        removed_index = (
            find_furthest_attraction(
                day_df
            )
        )


        if removed_index is None:

            print(
                "No attraction available "
                "for replacement."
            )

            break


        removed = (
            day_df.loc[
                removed_index
            ]
            .copy()
        )


        print(
            "Removing:",
            removed["name"]
        )


        replacement = (
            find_replacement(
                removed,
                day_df,
                candidates,
                used_place_ids
            )
        )


        if replacement is None:

            print(
                "No replacement found. "
                "Removing attraction."
            )

            day_df = (
                day_df.drop(
                    index=
                    removed_index
                )
                .reset_index(
                    drop=True
                )
            )


        else:

            print(
                "Replacing with:",
                replacement[
                    "name"
                ]
            )


            old_place_id = str(
                removed.get(
                    "place_id",
                    ""
                )
            )


            day_df = (
                apply_replacement(
                    day_df,
                    removed_index,
                    replacement
                )
            )


            new_place_id = str(
                replacement[
                    "place_id"
                ]
            )


            if old_place_id in used_place_ids:

                used_place_ids.discard(
                    old_place_id
                )


            used_place_ids.add(
                new_place_id
            )


        metrics = (
            get_route_metrics(
                day_df
            )
        )


        if metrics is None:
            break


        print(
            f"Updated: "
            f"{metrics['distance_km']:.2f} km / "
            f"{metrics['duration_minutes']:.1f} min"
        )


    return day_df, metrics


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":


    print("=" * 70)
    print("WAXN AI CONSTRAINED REPLANNER")
    print("=" * 70)


    itinerary = pd.read_csv(
        ITINERARY_FILE,
        low_memory=False
    )


    candidates = pd.read_csv(
        CANDIDATE_FILE,
        low_memory=False
    )


    used_place_ids = set(
        itinerary[
            "place_id"
        ]
        .dropna()
        .astype(str)
    )


    replanned_days = []

    report = []


    for day in sorted(
        itinerary[
            "day"
        ].unique()
    ):


        print(
            f"\nDAY {day}"
        )

        print(
            "-" * 70
        )


        day_df = (
            itinerary[
                itinerary["day"]
                ==
                day
            ]
            .copy()
        )


        replanned_day, metrics = (
            replan_day(
                day_df,
                candidates,
                used_place_ids
            )
        )


        replanned_day[
            "day"
        ] = day


        replanned_days.append(
            replanned_day
        )


        if metrics is not None:

            report.append({

                "day":
                    int(day),

                "distance_km":
                    round(
                        metrics[
                            "distance_km"
                        ],
                        2
                    ),

                "duration_minutes":
                    round(
                        metrics[
                            "duration_minutes"
                        ],
                        1
                    ),

                "within_distance_limit":
                    bool(
                        metrics[
                            "distance_km"
                        ]
                        <=
                        MAX_DAILY_DISTANCE_KM
                    ),

                "within_time_limit":
                    bool(
                        metrics[
                            "duration_minutes"
                        ]
                        <=
                        MAX_DAILY_DURATION_MIN
                    )
            })


    # ========================================================
    # FINAL ITINERARY
    # ========================================================

    final_itinerary = (
        pd.concat(
            replanned_days,
            ignore_index=True
        )
    )


    # Keep rows in day order
    if "time" in final_itinerary.columns:

        final_itinerary = (
            final_itinerary
            .sort_values(
                [
                    "day",
                    "time"
                ]
            )
            .reset_index(
                drop=True
            )
        )


    # ========================================================
    # SAVE
    # ========================================================

    itinerary_output = (
        PROCESSED_DIR
        / "waxn_constrained_itinerary.csv"
    )


    final_itinerary.to_csv(
        itinerary_output,
        index=False
    )


    report_output = (
        PROCESSED_DIR
        / "waxn_constrained_report.json"
    )


    with open(
        report_output,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2
        )


    # ========================================================
    # RESULTS
    # ========================================================

    print(
        "\n"
        "=" * 70
    )

    print(
        "FINAL RESULTS"
    )

    print(
        "=" * 70
    )


    for result in report:

        distance_status = (
            "OK"
            if result[
                "within_distance_limit"
            ]
            else "OVER"
        )

        time_status = (
            "OK"
            if result[
                "within_time_limit"
            ]
            else "OVER"
        )


        print(
            f"Day {result['day']}: "
            f"{result['distance_km']} km "
            f"[{distance_status}] / "
            f"{result['duration_minutes']} min "
            f"[{time_status}]"
        )


    print(
        "\nSaved:"
    )

    print(
        itinerary_output
    )

    print(
        report_output
    )


    print(
        "=" * 70
    )

    print(
        "WAXN AI CONSTRAINED REPLANNING COMPLETE"
    )

    print(
        "=" * 70
    )