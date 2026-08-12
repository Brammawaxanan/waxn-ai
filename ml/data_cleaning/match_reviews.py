from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"


# ============================================================
# LOAD DATA
# ============================================================

places = pd.read_csv(
    PROCESSED_DIR / "waxn_places_enriched.csv",
    low_memory=False
)

reviews = pd.read_csv(
    CLEAN_DIR / "reviews_clean.csv",
    low_memory=False
)


print("=" * 65)
print("WAXN AI REVIEW ↔ PLACE MATCHING V2")
print("=" * 65)

print("Places:", len(places))
print("Reviews:", len(reviews))


# ============================================================
# VALIDATION
# ============================================================

required_place_columns = [
    "place_id",
    "name",
    "name_key",
    "category"
]

for column in required_place_columns:

    if column not in places.columns:

        raise ValueError(
            f"Missing required place column: {column}"
        )


if "location_name_key" not in reviews.columns:

    raise ValueError(
        "reviews_clean.csv does not contain location_name_key"
    )


# ============================================================
# CLEAN KEYS
# ============================================================

places["name_key"] = (
    places["name_key"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)


reviews["location_name_key"] = (
    reviews["location_name_key"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)


# Optional location information from reviews

if "located_city" in reviews.columns:

    reviews["located_city_key"] = (
        reviews["located_city"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

else:

    reviews["located_city_key"] = ""


# ============================================================
# REVIEW ALIASES
# ============================================================

REVIEW_ALIASES = {

    "sigiriya the ancient rock fortress":
        "sigiriya",

    "temple of the sacred tooth relic":
        "temple of the tooth",

    "gangaramaya vihara buddhist temple":
        "gangaramaya temple",

    "hakgala botanic gardens":
        "hakgala botanical garden",

    "royal botanical gardens":
        "peradeniya botanical garden",

    "national zoological gardens of sri lanka":
        "dehiwala zoo",

    "baker s falls":
        "bakers falls",

    "lover s leap falls":
        "lovers leap",

    "ramboda waterfall":
        "ramboda falls",

    "brief garden bevis bawa":
        "brief garden",

    "damro labookellie tea centre and tea garden":
        "labookellie tea centre",

    "halpewatte tea factory tour":
        "halpewatte tea factory",

    "bluefield tea gardens":
        "blue field",

    "twin baths kuttam pokuna":
        "kuttam pokuna",

    "dagoba of thuparama":
        "thuparamaya",

    "jethawanaramaya stupa":
        "jetavanaramaya",

    "nallur kovil":
        "nallur kandaswamy",

    "koneswaram temple":
        "koneswaram",

    "samadhi statue":
        "samadhi buddha",

    "world buddhist museum":
        "international buddhist museum",

    "sea turtle farm galle mahamodara":
        "sea turtle farm",

    "victoria park of nuwara eliya":
        "victoria park",

    "community tsunami museum":
        "tsunami museum",

    "kelaniya raja maha vihara":
        "kelaniya temple",
}


# ============================================================
# BUILD PLACE NAME INDEX
# ============================================================

name_to_indices = {}


for index, row in places.iterrows():

    key = row["name_key"]

    if not key:
        continue

    name_to_indices.setdefault(
        key,
        []
    ).append(index)


all_place_names = list(
    name_to_indices.keys()
)


# ============================================================
# TOURISM / ATTRACTION INDEX
# ============================================================

tourism_categories = [
    "attraction",
    "activity"
]


tourism_places = places[
    places["category"].isin(
        tourism_categories
    )
].copy()


tourism_name_to_indices = {}


for index, row in tourism_places.iterrows():

    key = row["name_key"]

    if not key:
        continue

    tourism_name_to_indices.setdefault(
        key,
        []
    ).append(index)


tourism_names = list(
    tourism_name_to_indices.keys()
)


print(
    "Attraction/activity candidates:",
    len(tourism_places)
)


# ============================================================
# UNIQUE REVIEW LOCATIONS
# ============================================================

unique_review_locations = (
    reviews[
        reviews["location_name_key"] != ""
    ][
        "location_name_key"
    ]
    .drop_duplicates()
    .tolist()
)


print(
    "Unique review locations:",
    len(unique_review_locations)
)


# ============================================================
# MATCH CACHE
# ============================================================

location_match_cache = {}

match_audit = []


def save_match(
    review_location,
    place_index,
    score,
    match_type,
    searched_name
):

    place_id = places.at[
        place_index,
        "place_id"
    ]

    place_name = places.at[
        place_index,
        "name"
    ]

    category = places.at[
        place_index,
        "category"
    ]


    location_match_cache[
        review_location
    ] = {

        "place_id":
            place_id,

        "score":
            float(score),

        "type":
            match_type
    }


    match_audit.append({

        "review_location":
            review_location,

        "searched_name":
            searched_name,

        "matched_place_id":
            place_id,

        "matched_place_name":
            place_name,

        "category":
            category,

        "score":
            float(score),

        "match_type":
            match_type
    })


# ============================================================
# MATCHING
# ============================================================

for review_location in unique_review_locations:


    alias_name = REVIEW_ALIASES.get(
        review_location
    )


    search_names = [
        review_location
    ]


    if (
        alias_name
        and
        alias_name != review_location
    ):

        search_names.insert(
            0,
            alias_name
        )


    matched = False


    # ========================================================
    # 1. EXACT MATCH
    # ========================================================

    for search_name in search_names:

        candidates = name_to_indices.get(
            search_name,
            []
        )


        if len(candidates) == 1:

            save_match(

                review_location,
                candidates[0],
                100,
                (
                    "alias_exact"
                    if search_name != review_location
                    else "exact"
                ),
                search_name
            )

            matched = True
            break


    if matched:
        continue


    # ========================================================
    # 2. TOURISM / ATTRACTION FUZZY MATCH
    # ========================================================

    best_candidate = None


    for search_name in search_names:


        result = process.extractOne(

            search_name,
            tourism_names,

            scorer=fuzz.token_set_ratio
        )


        if result is None:
            continue


        matched_name = result[0]
        score = result[1]


        if (
            best_candidate is None
            or
            score > best_candidate["score"]
        ):

            best_candidate = {

                "searched_name":
                    search_name,

                "matched_name":
                    matched_name,

                "score":
                    score
            }


    if best_candidate is not None:


        score = best_candidate[
            "score"
        ]


        # Alias matches can use a slightly lower threshold
        threshold = (
            88
            if best_candidate[
                "searched_name"
            ] != review_location
            else 90
        )


        if score >= threshold:


            candidates = (
                tourism_name_to_indices[
                    best_candidate[
                        "matched_name"
                    ]
                ]
            )


            # Only accept unambiguous result
            if len(candidates) == 1:


                save_match(

                    review_location,

                    candidates[0],

                    score,

                    "attraction_fuzzy",

                    best_candidate[
                        "searched_name"
                    ]
                )


                continue


    # ========================================================
    # 3. STRICT GENERAL FUZZY MATCH
    # ========================================================

    best_general = None


    for search_name in search_names:


        result = process.extractOne(

            search_name,
            all_place_names,

            scorer=fuzz.token_sort_ratio
        )


        if result is None:
            continue


        matched_name = result[0]
        score = result[1]


        if (
            best_general is None
            or
            score > best_general["score"]
        ):

            best_general = {

                "searched_name":
                    search_name,

                "matched_name":
                    matched_name,

                "score":
                    score
            }


    if (
        best_general is not None
        and
        best_general["score"] >= 95
    ):


        candidates = name_to_indices[
            best_general[
                "matched_name"
            ]
        ]


        if len(candidates) == 1:


            save_match(

                review_location,

                candidates[0],

                best_general[
                    "score"
                ],

                "general_fuzzy",

                best_general[
                    "searched_name"
                ]
            )


# ============================================================
# APPLY MATCHES TO REVIEWS
# ============================================================

reviews["matched_place_id"] = pd.NA
reviews["place_match_score"] = pd.NA
reviews["place_match_type"] = pd.NA


for index, row in reviews.iterrows():


    location_key = row[
        "location_name_key"
    ]


    match = location_match_cache.get(
        location_key
    )


    if match is None:
        continue


    reviews.at[
        index,
        "matched_place_id"
    ] = match["place_id"]


    reviews.at[
        index,
        "place_match_score"
    ] = match["score"]


    reviews.at[
        index,
        "place_match_type"
    ] = match["type"]


# ============================================================
# MATCH RESULTS
# ============================================================

matched_reviews = reviews[
    reviews[
        "matched_place_id"
    ].notna()
].copy()


unmatched_reviews = reviews[
    reviews[
        "matched_place_id"
    ].isna()
].copy()


matched_unique_locations = len(
    location_match_cache
)


unmatched_unique_locations = (
    len(unique_review_locations)
    -
    matched_unique_locations
)


print("\n" + "=" * 65)
print("MATCHING RESULTS")
print("=" * 65)


print(
    "Matched unique locations:",
    matched_unique_locations
)


print(
    "Unmatched unique locations:",
    unmatched_unique_locations
)


print(
    "Matched reviews:",
    len(matched_reviews)
)


print(
    "Unmatched reviews:",
    len(unmatched_reviews)
)


coverage = (
    len(matched_reviews)
    /
    len(reviews)
    *
    100
)


print(
    "Review coverage:",
    f"{coverage:.2f}%"
)


# ============================================================
# MATCH TYPE COUNTS
# ============================================================

if not matched_reviews.empty:

    print(
        "\nMatch types:"
    )

    print(
        matched_reviews[
            "place_match_type"
        ].value_counts()
    )


# ============================================================
# REVIEW STATISTICS PER PLACE
# ============================================================

if not matched_reviews.empty:


    place_stats = (

        matched_reviews

        .groupby(
            "matched_place_id"
        )

        .agg(

            avg_rating=(
                "rating",
                "mean"
            ),

            review_count=(
                "rating",
                "count"
            )
        )

        .reset_index()
    )


    if "helpful_votes" in matched_reviews.columns:


        helpful_stats = (

            matched_reviews

            .groupby(
                "matched_place_id"
            )[
                "helpful_votes"
            ]

            .sum()

            .reset_index(
                name=
                "helpful_votes_sum"
            )
        )


        place_stats = (
            place_stats.merge(

                helpful_stats,

                on=
                "matched_place_id",

                how=
                "left"
            )
        )


else:


    place_stats = pd.DataFrame(

        columns=[

            "matched_place_id",

            "avg_rating",

            "review_count",

            "helpful_votes_sum"
        ]
    )


# ============================================================
# BETTER POPULARITY SCORE
# ============================================================

if not place_stats.empty:


    max_reviews = (
        place_stats[
            "review_count"
        ].max()
    )


    if max_reviews > 0:


        place_stats[
            "review_popularity"
        ] = (

            place_stats[
                "review_count"
            ]

            /
            max_reviews
        )


    else:

        place_stats[
            "review_popularity"
        ] = 0


# ============================================================
# MERGE REVIEW FEATURES INTO PLACES
# ============================================================

places_with_reviews = (

    places.merge(

        place_stats,

        left_on=
        "place_id",

        right_on=
        "matched_place_id",

        how=
        "left"
    )
)


places_with_reviews = (

    places_with_reviews.drop(

        columns=[
            "matched_place_id"
        ],

        errors=
        "ignore"
    )
)


# ============================================================
# CLEAN FEATURE VALUES
# ============================================================

if "avg_rating" in places_with_reviews.columns:


    places_with_reviews[
        "avg_rating"
    ] = (

        places_with_reviews[
            "avg_rating"
        ].round(2)
    )


if "review_count" in places_with_reviews.columns:


    places_with_reviews[
        "review_count"
    ] = (

        places_with_reviews[
            "review_count"
        ]

        .fillna(0)

        .astype(int)
    )


if "helpful_votes_sum" in places_with_reviews.columns:


    places_with_reviews[
        "helpful_votes_sum"
    ] = (

        places_with_reviews[
            "helpful_votes_sum"
        ]

        .fillna(0)
    )


if "review_popularity" in places_with_reviews.columns:


    places_with_reviews[
        "review_popularity"
    ] = (

        places_with_reviews[
            "review_popularity"
        ]

        .fillna(0)

        .round(4)
    )


# ============================================================
# SAVE MATCHED REVIEWS
# ============================================================

reviews.to_csv(

    PROCESSED_DIR
    / "waxn_reviews_matched.csv",

    index=False
)


# ============================================================
# SAVE PLACES WITH REVIEW FEATURES
# ============================================================

places_with_reviews.to_csv(

    PROCESSED_DIR
    / "waxn_places_with_reviews.csv",

    index=False
)


# ============================================================
# SAVE UNMATCHED REVIEWS
# ============================================================

unmatched_reviews.to_csv(

    PROCESSED_DIR
    / "unmatched_reviews.csv",

    index=False
)


# ============================================================
# SAVE MATCH AUDIT
# ============================================================

match_audit_df = pd.DataFrame(
    match_audit
)


match_audit_df.to_csv(

    PROCESSED_DIR
    / "review_place_match_audit.csv",

    index=False
)


# ============================================================
# UNMATCHED UNIQUE LOCATIONS
# ============================================================

unmatched_unique = (

    unmatched_reviews[
        [
            "location_name",
            "location_name_key"
        ]
    ]

    .drop_duplicates()

    .sort_values(
        "location_name"
    )
)


unmatched_unique.to_csv(

    PROCESSED_DIR
    / "unmatched_review_locations.csv",

    index=False
)


# ============================================================
# FINAL OUTPUT
# ============================================================

print("\nSaved:")

print(
    "data/processed/waxn_reviews_matched.csv"
)

print(
    "data/processed/waxn_places_with_reviews.csv"
)

print(
    "data/processed/unmatched_reviews.csv"
)

print(
    "data/processed/review_place_match_audit.csv"
)

print(
    "data/processed/unmatched_review_locations.csv"
)


print(
    "\nUNMATCHED UNIQUE REVIEW LOCATIONS"
)

print("=" * 65)


if unmatched_unique.empty:

    print(
        "All review locations matched."
    )

else:

    print(
        unmatched_unique.to_string(
            index=False
        )
    )


print("=" * 65)
print("WAXN AI REVIEW MATCHING V2 COMPLETE")
print("=" * 65)