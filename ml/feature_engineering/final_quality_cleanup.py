from pathlib import Path
import re
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = (
    PROCESSED_DIR
    / "waxn_recommendation_candidates.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "waxn_final_candidates.csv"
)


places = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)


print("=" * 70)
print("WAXN AI FINAL CANDIDATE QUALITY CLEANUP")
print("=" * 70)

print("Before:", len(places))


GENERIC_EXACT_NAMES = {
    "temple",
    "viewpoint",
    "view point",
    "restaurant",
    "hotel",
    "guest house",
    "cafe",
    "shop",
    "park",
    "garden",
    "museum",
    "information",
    "attraction",
    "tourist attraction",
    "resort",
    "hostel",
}


BAD_PHRASES = [
    "free entry",
    "via steps",
    "passing large rocks",
    "viewpoint rock",
    "railway trek",
    "unknown",
    "unnamed",
    "no name",
]


def normalize_name(name):

    if pd.isna(name):
        return ""

    return (
        str(name)
        .strip()
        .lower()
    )


def is_low_quality_name(name):

    text = normalize_name(name)

    if not text:
        return True

    if len(text) < 4:
        return True

    if text in GENERIC_EXACT_NAMES:
        return True

    if any(
        phrase in text
        for phrase in BAD_PHRASES
    ):
        return True

    # numbers/symbols only
    if not re.search(
        r"[a-zA-Z]",
        text
    ):
        return True

    return False


places["final_bad_name"] = (
    places["name"]
    .apply(
        is_low_quality_name
    )
)


# ------------------------------------------------------------
# Additional quality rules for attractions
# ------------------------------------------------------------

attraction_mask = (
    places["category"]
    .isin(
        [
            "attraction",
            "activity"
        ]
    )
)


# If attraction has weak name AND no reviews,
# strongly exclude it
places["final_eligible"] = True


places.loc[
    places["final_bad_name"],
    "final_eligible"
] = False


if "review_count" in places.columns:

    places["review_count"] = (
        places["review_count"]
        .fillna(0)
    )


# Make sure map coordinates exist
places.loc[
    places["latitude"].isna()
    |
    places["longitude"].isna(),
    "final_eligible"
] = False


# ------------------------------------------------------------
# Keep only final eligible
# ------------------------------------------------------------

final_places = (
    places[
        places["final_eligible"]
    ]
    .copy()
)


final_places = (
    final_places
    .drop(
        columns=[
            "final_bad_name",
            "final_eligible"
        ],
        errors="ignore"
    )
)


final_places.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "Removed:",
    len(places) - len(final_places)
)

print(
    "After:",
    len(final_places)
)


print("\nFinal category counts:")

print(
    final_places[
        "category"
    ].value_counts()
)


print("\nSaved:")
print(
    OUTPUT_FILE
)

print("=" * 70)
print("FINAL QUALITY CLEANUP COMPLETE")
print("=" * 70)