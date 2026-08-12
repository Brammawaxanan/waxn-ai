from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

DATA_PATH = PROCESSED_DIR / "waxn_recommendation_candidates.csv"


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
# LOAD DATA ONCE
# ============================================================

places = pd.read_csv(
    DATA_PATH,
    low_memory=False
)

places[FEATURE_COLUMNS] = (
    places[FEATURE_COLUMNS]
    .fillna(0)
    .astype(float)
)

places["quality_score"] = (
    places["quality_score"]
    .fillna(0)
    .astype(float)
)

places["data_quality_score"] = (
    places["data_quality_score"]
    .fillna(0)
    .astype(float)
)


# ============================================================
# MAIN RECOMMENDER
# ============================================================

def recommend_places(
    district=None,
    city=None,
    nature=0.5,
    adventure=0.5,
    history=0.5,
    photography=0.5,
    food=0.5,
    relaxation=0.5,
    family=0.5,
    shopping=0.5,
    categories=None,
    top_n=10,
):

    data = places.copy()


    # --------------------------------------------------------
    # LOCATION FILTER
    # --------------------------------------------------------

    if district:

        data = data[
            data["district"]
            .fillna("")
            .str.lower()
            .eq(district.lower())
        ].copy()


    if city:

        city_matches = data[
            data["city"]
            .fillna("")
            .str.lower()
            .eq(city.lower())
        ]

        # Only apply city filter if records actually exist.
        if not city_matches.empty:
            data = city_matches.copy()


    # --------------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------------

    if categories:

        data = data[
            data["category"].isin(categories)
        ].copy()


    if data.empty:
        return pd.DataFrame()


    # --------------------------------------------------------
    # USER VECTOR
    # --------------------------------------------------------

    user_preferences = {
        "nature_score": nature,
        "adventure_score": adventure,
        "history_score": history,
        "photography_score": photography,
        "food_score": food,
        "relaxation_score": relaxation,
        "family_score": family,
        "shopping_score": shopping,
    }


    user_vector = np.array(
        [
            user_preferences[column]
            for column in FEATURE_COLUMNS
        ],
        dtype=float
    ).reshape(1, -1)


    # --------------------------------------------------------
    # PLACE MATRIX
    # --------------------------------------------------------

    place_matrix = (
        data[FEATURE_COLUMNS]
        .values
    )


    # --------------------------------------------------------
    # COSINE SIMILARITY
    # --------------------------------------------------------

    similarity = cosine_similarity(
        place_matrix,
        user_vector
    ).flatten()


    data["preference_score"] = similarity


    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    data["recommendation_score"] = (
        data["preference_score"] * 0.65
        +
        data["quality_score"] * 0.20
        +
        data["data_quality_score"] * 0.15
    )


    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    results = (
        data
        .sort_values(
            "recommendation_score",
            ascending=False
        )
        .head(top_n)
        .copy()
    )


    return results


# ============================================================
# CATEGORY-SPECIFIC FUNCTIONS
# ============================================================

def recommend_attractions(
    district,
    **preferences
):

    return recommend_places(
        district=district,
        categories=[
            "attraction",
            "activity"
        ],
        **preferences
    )


def recommend_food(
    district,
    **preferences
):

    return recommend_places(
        district=district,
        categories=[
            "food"
        ],
        **preferences
    )


def recommend_hotels(
    district,
    **preferences
):

    return recommend_places(
        district=district,
        categories=[
            "accommodation"
        ],
        **preferences
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("WAXN AI DYNAMIC RECOMMENDER")
    print("=" * 70)


    user_preferences = {

        "nature": 0.9,
        "adventure": 0.8,
        "history": 0.3,
        "photography": 1.0,
        "food": 0.7,
        "relaxation": 0.5,
        "family": 0.2,
        "shopping": 0.1,
        "top_n": 10
    }


    print("\nTOP ATTRACTIONS - BADULLA")
    print("=" * 70)

    attractions = recommend_attractions(
        district="Badulla",
        **user_preferences
    )


    print(
        attractions[
            [
                "place_id",
                "name",
                "category",
                "subcategory",
                "district",
                "latitude",
                "longitude",
                "avg_rating",
                "review_count",
                "preference_score",
                "quality_score",
                "data_quality_score",
                "recommendation_score"
            ]
        ].to_string(
            index=False
        )
    )


    print("\nTOP FOOD - BADULLA")
    print("=" * 70)

    food = recommend_food(
        district="Badulla",
        **user_preferences
    )


    print(
        food[
            [
                "place_id",
                "name",
                "district",
                "latitude",
                "longitude",
                "avg_rating",
                "review_count",
                "recommendation_score"
            ]
        ].to_string(
            index=False
        )
    )


    print("\nTOP HOTELS - BADULLA")
    print("=" * 70)

    hotels = recommend_hotels(
        district="Badulla",
        **user_preferences
    )


    print(
        hotels[
            [
                "place_id",
                "name",
                "subcategory",
                "district",
                "latitude",
                "longitude",
                "avg_rating",
                "review_count",
                "recommendation_score"
            ]
        ].to_string(
            index=False
        )
    )


    print("=" * 70)
    print("DYNAMIC RECOMMENDER TEST COMPLETE")
    print("=" * 70)