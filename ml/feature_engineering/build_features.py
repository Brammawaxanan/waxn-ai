from pathlib import Path
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# LOAD DATA
# ============================================================

places = pd.read_csv(
    PROCESSED_DIR / "waxn_places_with_reviews.csv",
    low_memory=False
)

print("=" * 65)
print("WAXN AI FEATURE ENGINEERING")
print("=" * 65)

print("Places:", len(places))


# ============================================================
# HELPER
# ============================================================

def contains_any(text, keywords):

    if pd.isna(text):
        return False

    text = str(text).lower()

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# COMBINED TEXT
# ============================================================

places["feature_text"] = (
    places["name"].fillna("").astype(str)
    + " "
    + places["category"].fillna("").astype(str)
    + " "
    + places["subcategory"].fillna("").astype(str)
)


# ============================================================
# INITIAL SCORES
# ============================================================

score_columns = [
    "nature_score",
    "adventure_score",
    "history_score",
    "photography_score",
    "food_score",
    "relaxation_score",
    "family_score",
    "shopping_score"
]

for column in score_columns:
    places[column] = 0.0


# ============================================================
# KEYWORDS
# ============================================================

nature_keywords = [
    "beach",
    "waterfall",
    "falls",
    "forest",
    "park",
    "garden",
    "lake",
    "river",
    "mountain",
    "rock",
    "viewpoint",
    "nature",
    "wildlife",
    "sanctuary",
    "national park",
    "botanical"
]

adventure_keywords = [
    "hiking",
    "trek",
    "climbing",
    "rock",
    "surf",
    "water sports",
    "rafting",
    "safari",
    "diving",
    "snorkel",
    "adventure",
    "camp",
    "trail"
]

history_keywords = [
    "temple",
    "kovil",
    "vihara",
    "stupa",
    "dagaba",
    "museum",
    "fort",
    "heritage",
    "ancient",
    "historic",
    "monastery",
    "church",
    "mosque",
    "palace"
]

photography_keywords = [
    "viewpoint",
    "beach",
    "waterfall",
    "falls",
    "mountain",
    "garden",
    "lake",
    "rock",
    "fort",
    "bridge",
    "sunset",
    "scenic"
]

relaxation_keywords = [
    "spa",
    "wellness",
    "beach",
    "garden",
    "resort",
    "lake",
    "park",
    "relax"
]

family_keywords = [
    "zoo",
    "aquarium",
    "park",
    "garden",
    "museum",
    "beach",
    "family",
    "theme park"
]


# ============================================================
# RULE BASED FEATURE SCORES
# ============================================================

for index, row in places.iterrows():

    text = row["feature_text"]

    category = str(
        row.get("category", "")
    ).lower()


    # --------------------------------------------------------
    # Nature
    # --------------------------------------------------------

    if contains_any(
        text,
        nature_keywords
    ):
        places.at[
            index,
            "nature_score"
        ] += 0.8


    # --------------------------------------------------------
    # Adventure
    # --------------------------------------------------------

    if contains_any(
        text,
        adventure_keywords
    ):
        places.at[
            index,
            "adventure_score"
        ] += 0.8


    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    if contains_any(
        text,
        history_keywords
    ):
        places.at[
            index,
            "history_score"
        ] += 0.9


    # --------------------------------------------------------
    # Photography
    # --------------------------------------------------------

    if contains_any(
        text,
        photography_keywords
    ):
        places.at[
            index,
            "photography_score"
        ] += 0.8


    # --------------------------------------------------------
    # Relaxation
    # --------------------------------------------------------

    if contains_any(
        text,
        relaxation_keywords
    ):
        places.at[
            index,
            "relaxation_score"
        ] += 0.8


    # --------------------------------------------------------
    # Family
    # --------------------------------------------------------

    if contains_any(
        text,
        family_keywords
    ):
        places.at[
            index,
            "family_score"
        ] += 0.7


    # --------------------------------------------------------
    # Food
    # --------------------------------------------------------

    if category == "food":

        places.at[
            index,
            "food_score"
        ] = 1.0


    # --------------------------------------------------------
    # Shopping
    # --------------------------------------------------------

    if category == "shopping":

        places.at[
            index,
            "shopping_score"
        ] = 1.0


# ============================================================
# CATEGORY BOOSTS
# ============================================================

activity_mask = (
    places["category"] == "activity"
)

places.loc[
    activity_mask,
    "adventure_score"
] += 0.2


attraction_mask = (
    places["category"] == "attraction"
)

places.loc[
    attraction_mask,
    "photography_score"
] += 0.2


# ============================================================
# CLIP VALUES
# ============================================================

for column in score_columns:

    places[column] = (
        places[column]
        .clip(
            lower=0,
            upper=1
        )
        .round(2)
    )


# ============================================================
# REVIEW QUALITY SCORE
# ============================================================

places["rating_score"] = (
    places["avg_rating"]
    .fillna(0)
    / 5
)


places["review_count"] = (
    places["review_count"]
    .fillna(0)
)


places["review_popularity"] = (
    places["review_popularity"]
    .fillna(0)
)


places["quality_score"] = (
    (
        places["rating_score"]
        * 0.7
    )
    +
    (
        places["review_popularity"]
        * 0.3
    )
).round(4)


# ============================================================
# WEATHER SENSITIVITY
# ============================================================

places["weather_sensitive"] = False


weather_keywords = [
    "beach",
    "waterfall",
    "falls",
    "hiking",
    "trek",
    "viewpoint",
    "national park",
    "forest",
    "garden",
    "water sports",
    "surf",
    "safari",
    "rock"
]


for index, row in places.iterrows():

    if contains_any(
        row["feature_text"],
        weather_keywords
    ):

        places.at[
            index,
            "weather_sensitive"
        ] = True


# ============================================================
# INDOOR / OUTDOOR
# ============================================================

places["environment"] = "unknown"


indoor_keywords = [
    "museum",
    "restaurant",
    "cafe",
    "spa",
    "shop",
    "hotel",
    "gallery"
]


outdoor_keywords = [
    "beach",
    "waterfall",
    "falls",
    "park",
    "garden",
    "forest",
    "viewpoint",
    "mountain",
    "rock",
    "lake",
    "safari"
]


for index, row in places.iterrows():

    text = row["feature_text"]


    if contains_any(
        text,
        indoor_keywords
    ):

        places.at[
            index,
            "environment"
        ] = "indoor"


    if contains_any(
        text,
        outdoor_keywords
    ):

        places.at[
            index,
            "environment"
        ] = "outdoor"


# ============================================================
# MAP READY FLAG
# ============================================================

places["map_ready"] = (
    places["latitude"].notna()
    &
    places["longitude"].notna()
)


# ============================================================
# FINAL ML FEATURE DATA
# ============================================================

ml_columns = [

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
    "review_popularity",
    "quality_score",

    "nature_score",
    "adventure_score",
    "history_score",
    "photography_score",
    "food_score",
    "relaxation_score",
    "family_score",
    "shopping_score",

    "weather_sensitive",
    "environment",
    "map_ready",

    "feature_text"
]


ml_features = places[
    [
        column
        for column in ml_columns
        if column in places.columns
    ]
].copy()


# ============================================================
# SAVE
# ============================================================

output_path = (
    PROCESSED_DIR
    / "waxn_ml_features.csv"
)


ml_features.to_csv(
    output_path,
    index=False
)


print("\nSaved:")
print(
    "data/processed/waxn_ml_features.csv"
)


print("\nFeature counts:")

print(
    ml_features[
        [
            "nature_score",
            "adventure_score",
            "history_score",
            "photography_score",
            "food_score",
            "relaxation_score",
            "family_score",
            "shopping_score"
        ]
    ]
    .gt(0)
    .sum()
)


print("\nMap ready:")

print(
    ml_features[
        "map_ready"
    ]
    .value_counts()
)


print("\nWeather sensitive:")

print(
    ml_features[
        "weather_sensitive"
    ]
    .value_counts()
)


print("=" * 65)
print("WAXN AI FEATURE ENGINEERING COMPLETE")
print("=" * 65)