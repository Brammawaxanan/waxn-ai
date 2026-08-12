from pathlib import Path
import re
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# ============================================================
# LOAD
# ============================================================

places = pd.read_csv(
    PROCESSED_DIR / "waxn_ml_features.csv",
    low_memory=False
)

print("=" * 65)
print("WAXN AI PLACE QUALITY FILTER")
print("=" * 65)

print("Before filtering:", len(places))


# ============================================================
# BAD / GENERIC NAME RULES
# ============================================================

GENERIC_NAMES = {
    "viewpoint",
    "view point",
    "restaurant",
    "hotel",
    "guest house",
    "shop",
    "cafe",
    "park",
    "garden",
    "information",
    "attraction",
    "tourist attraction",
}


BAD_PHRASES = [
    "free entry",
    "via steps",
    "passing large rocks",
    "no name",
    "unnamed",
    "unknown",
]


def is_bad_name(name):

    if pd.isna(name):
        return True

    text = str(name).strip().lower()

    if len(text) < 3:
        return True

    if text in GENERIC_NAMES:
        return True

    if any(
        phrase in text
        for phrase in BAD_PHRASES
    ):
        return True

    # Only numbers / symbols
    if not re.search(
        r"[a-zA-Z]",
        text
    ):
        return True

    return False


# ============================================================
# NAME QUALITY
# ============================================================

places["bad_name"] = (
    places["name"]
    .apply(is_bad_name)
)


# ============================================================
# MAP REQUIREMENT
# ============================================================

places["coordinate_ok"] = (
    places["latitude"].notna()
    &
    places["longitude"].notna()
)


# ============================================================
# RECOMMENDATION ELIGIBILITY
# ============================================================

places["recommendation_eligible"] = True


# Bad names should never be recommended
places.loc[
    places["bad_name"],
    "recommendation_eligible"
] = False


# Map is essential for WAXN itinerary
places.loc[
    ~places["coordinate_ok"],
    "recommendation_eligible"
] = False


# ============================================================
# BASIC TOURISM QUALITY SCORE
# ============================================================

places["data_quality_score"] = 0.0


# Good proper name
places.loc[
    ~places["bad_name"],
    "data_quality_score"
] += 0.30


# Coordinates
places.loc[
    places["coordinate_ok"],
    "data_quality_score"
] += 0.30


# District available
places.loc[
    places["district"].notna(),
    "data_quality_score"
] += 0.10


# Review information
places.loc[
    places["review_count"].fillna(0) > 0,
    "data_quality_score"
] += 0.20


# Subcategory
places.loc[
    places["subcategory"].notna(),
    "data_quality_score"
] += 0.10


places["data_quality_score"] = (
    places["data_quality_score"]
    .clip(0, 1)
    .round(2)
)


# ============================================================
# SAVE
# ============================================================

eligible = places[
    places["recommendation_eligible"]
].copy()


places.to_csv(
    PROCESSED_DIR / "waxn_ml_features_quality.csv",
    index=False
)


eligible.to_csv(
    PROCESSED_DIR / "waxn_recommendation_candidates.csv",
    index=False
)


print("\nBad names:")
print(
    places["bad_name"]
    .value_counts()
)


print("\nRecommendation eligible:")
print(
    places["recommendation_eligible"]
    .value_counts()
)


print("\nCategory counts:")
print(
    eligible["category"]
    .value_counts()
)


print("\nSaved:")
print(
    "data/processed/waxn_ml_features_quality.csv"
)

print(
    "data/processed/waxn_recommendation_candidates.csv"
)

print("=" * 65)
print("QUALITY FILTER COMPLETE")
print("=" * 65)