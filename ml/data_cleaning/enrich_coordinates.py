from pathlib import Path
import pandas as pd
from rapidfuzz import fuzz, process

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"


# ------------------------------------------------
# Load datasets
# ------------------------------------------------

places = pd.read_csv(
    PROCESSED_DIR / "waxn_places.csv",
    low_memory=False
)

osm = pd.read_csv(
    CLEAN_DIR / "poi_clean.csv",
    low_memory=False
)


print("=" * 60)
print("WAXN AI COORDINATE ENRICHMENT")
print("=" * 60)

print("Master places:", len(places))
print("OSM POIs:", len(osm))


# ------------------------------------------------
# Helper functions
# ------------------------------------------------

def normalize(value):

    if pd.isna(value):
        return ""

    return (
        str(value)
        .lower()
        .strip()
    )


def compatible_category(master_category, osm_category):

    if master_category == osm_category:
        return True

    # Activities and attractions can overlap
    if {
        master_category,
        osm_category
    } <= {"activity", "attraction"}:
        return True

    return False


# ------------------------------------------------
# Prepare OSM
# ------------------------------------------------

osm["name_key"] = (
    osm["name_key"]
    .fillna("")
    .astype(str)
)

osm["district_key"] = (
    osm["district"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

osm = osm[
    osm["latitude"].notna()
    &
    osm["longitude"].notna()
].copy()


# ------------------------------------------------
# Find missing coordinates
# ------------------------------------------------

missing_mask = (
    places["latitude"].isna()
    |
    places["longitude"].isna()
)

missing_count_before = missing_mask.sum()

print(
    "\nMissing before enrichment:",
    missing_count_before
)


# ------------------------------------------------
# Matching
# ------------------------------------------------

matches_found = 0
high_confidence_matches = 0

places["coordinate_match_score"] = pd.NA
places["coordinate_source"] = pd.NA


for index, row in places[missing_mask].iterrows():

    target_name = normalize(
        row.get("name_key")
    )

    target_district = normalize(
        row.get("district")
    )

    target_category = normalize(
        row.get("category")
    )

    if not target_name:
        continue


    # --------------------------------------------
    # Candidate filter by category
    # --------------------------------------------

    candidates = osm[
        osm["category"].apply(
            lambda category:
            compatible_category(
                target_category,
                normalize(category)
            )
        )
    ].copy()


    if candidates.empty:
        continue


    # --------------------------------------------
    # District filter
    # --------------------------------------------

    if target_district:

        district_candidates = candidates[
            candidates["district_key"]
            ==
            target_district
        ]

        if not district_candidates.empty:

            candidates = district_candidates


    if candidates.empty:
        continue


    # --------------------------------------------
    # Exact name match first
    # --------------------------------------------

    exact_matches = candidates[
        candidates["name_key"]
        ==
        target_name
    ]


    if len(exact_matches) == 1:

        match = exact_matches.iloc[0]

        places.at[
            index,
            "latitude"
        ] = match["latitude"]

        places.at[
            index,
            "longitude"
        ] = match["longitude"]

        places.at[
            index,
            "coordinate_match_score"
        ] = 100

        places.at[
            index,
            "coordinate_source"
        ] = "osm_exact_match"

        matches_found += 1
        high_confidence_matches += 1

        continue


    # --------------------------------------------
    # Fuzzy match
    # --------------------------------------------

    candidate_names = (
        candidates["name_key"]
        .dropna()
        .astype(str)
        .tolist()
    )


    if not candidate_names:
        continue


    best_match = process.extractOne(
        target_name,
        candidate_names,
        scorer=fuzz.token_sort_ratio
    )


    if best_match is None:
        continue


    matched_name = best_match[0]
    score = best_match[1]


    # --------------------------------------------
    # Safe threshold
    # --------------------------------------------

    if score < 92:
        continue


    selected = candidates[
        candidates["name_key"]
        ==
        matched_name
    ]


    if len(selected) != 1:
        continue


    match = selected.iloc[0]


    places.at[
        index,
        "latitude"
    ] = match["latitude"]

    places.at[
        index,
        "longitude"
    ] = match["longitude"]

    places.at[
        index,
        "coordinate_match_score"
    ] = score

    places.at[
        index,
        "coordinate_source"
    ] = "osm_fuzzy_match"


    matches_found += 1

    if score >= 95:
        high_confidence_matches += 1


# ------------------------------------------------
# Save
# ------------------------------------------------

missing_after = (
    places["latitude"].isna()
    |
    places["longitude"].isna()
).sum()


places.to_csv(
    PROCESSED_DIR / "waxn_places_enriched.csv",
    index=False
)


print("\n" + "=" * 60)
print("COORDINATE ENRICHMENT COMPLETE")
print("=" * 60)

print(
    "Missing before:",
    missing_count_before
)

print(
    "Coordinates matched:",
    matches_found
)

print(
    "High confidence matches:",
    high_confidence_matches
)

print(
    "Missing after:",
    missing_after
)

print(
    "Coverage:",
    f"{((len(places) - missing_after) / len(places) * 100):.2f}%"
)

print("=" * 60)