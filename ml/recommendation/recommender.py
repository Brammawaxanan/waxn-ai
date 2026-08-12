from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# LOAD DATA
# ============================================================

places = pd.read_csv(
    PROCESSED_DIR / "waxn_ml_features.csv",
    low_memory=False
)


print("=" * 65)
print("WAXN AI RECOMMENDATION MODEL V1")
print("=" * 65)

print("Places:", len(places))


# ============================================================
# FEATURE COLUMNS
# ============================================================

FEATURE_COLUMNS = [
    "nature_score",
    "adventure_score",
    "history_score",
    "photography_score",
    "food_score",
    "relaxation_score",
    "family_score",
    "shopping_score",
]


# ============================================================
# CLEAN FEATURES
# ============================================================

places[FEATURE_COLUMNS] = (
    places[FEATURE_COLUMNS]
    .fillna(0)
    .astype(float)
)


# ============================================================
# USER PREFERENCE
# ============================================================

user_preferences = {

    "nature_score": 0.9,

    "adventure_score": 0.8,

    "history_score": 0.3,

    "photography_score": 1.0,

    "food_score": 0.7,

    "relaxation_score": 0.5,

    "family_score": 0.2,

    "shopping_score": 0.1,
}


user_vector = np.array(
    [
        user_preferences[column]
        for column in FEATURE_COLUMNS
    ]
).reshape(1, -1)


# ============================================================
# PLACE FEATURE MATRIX
# ============================================================

place_matrix = places[
    FEATURE_COLUMNS
].values


# ============================================================
# COSINE SIMILARITY
# ============================================================

similarity_scores = cosine_similarity(
    place_matrix,
    user_vector
).flatten()


places["preference_score"] = similarity_scores


# ============================================================
# QUALITY SCORE
# ============================================================

places["quality_score"] = (
    places["quality_score"]
    .fillna(0)
)


# ============================================================
# FINAL RECOMMENDATION SCORE
# ============================================================

places["recommendation_score"] = (

    places["preference_score"] * 0.75

    +

    places["quality_score"] * 0.25
)


# ============================================================
# MAP READY FILTER
# ============================================================

places = places[
    places["map_ready"] == True
].copy()


# ============================================================
# OPTIONAL: FILTER ONE DISTRICT
# ============================================================

TARGET_DISTRICT = "Badulla"


district_places = places[
    places["district"]
    .fillna("")
    .str.lower()
    ==
    TARGET_DISTRICT.lower()
].copy()


print(
    "\nPlaces in district:",
    len(district_places)
)


# ============================================================
# REMOVE FOOD / HOTEL FOR ATTRACTION TEST
# ============================================================

attractions = district_places[
    district_places["category"].isin(
        [
            "attraction",
            "activity"
        ]
    )
].copy()


# ============================================================
# SORT
# ============================================================

recommendations = (
    attractions
    .sort_values(
        "recommendation_score",
        ascending=False
    )
    .head(10)
)


# ============================================================
# SHOW RESULTS
# ============================================================

display_columns = [

    "place_id",

    "name",

    "category",

    "subcategory",

    "district",

    "city",

    "latitude",

    "longitude",

    "avg_rating",

    "review_count",

    "preference_score",

    "quality_score",

    "recommendation_score"
]


display_columns = [
    column
    for column in display_columns
    if column in recommendations.columns
]


print("\nTOP 10 RECOMMENDATIONS")
print("=" * 65)

print(
    recommendations[
        display_columns
    ].to_string(
        index=False
    )
)


# ============================================================
# SAVE TEST RESULTS
# ============================================================

recommendations.to_csv(

    PROCESSED_DIR
    / "waxn_test_recommendations.csv",

    index=False
)


print("\nSaved:")
print(
    "data/processed/waxn_test_recommendations.csv"
)

print("=" * 65)