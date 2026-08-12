from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"

places = pd.read_csv(
    PROCESSED_DIR / "waxn_places.csv"
)

reviews = pd.read_csv(
    CLEAN_DIR / "reviews_clean.csv",
    low_memory=False
)

print("=" * 60)
print("WAXN AI DATA VALIDATION")
print("=" * 60)

print("\nTotal places:")
print(len(places))

print("\nCategory counts:")
print(
    places["category"]
    .value_counts()
)

print("\nMissing values:")
print(
    places.isna()
    .sum()
    .sort_values(ascending=False)
)

print("\nMissing coordinates:")
missing_coordinates = places[
    places["latitude"].isna()
    |
    places["longitude"].isna()
]

print(len(missing_coordinates))

print("\nPlaces with coordinates:")
with_coordinates = places[
    places["latitude"].notna()
    &
    places["longitude"].notna()
]

print(len(with_coordinates))

print("\nMissing district:")
print(
    places["district"]
    .isna()
    .sum()
)

print("\nMissing city:")
print(
    places["city"]
    .isna()
    .sum()
)

print("\nDuplicate normalized names:")
duplicates = (
    places[
        places.duplicated(
            subset=[
                "name_key",
                "category",
                "district"
            ],
            keep=False
        )
    ]
)

print(len(duplicates))

print("\nReviews:")
print(len(reviews))

print("=" * 60)

print("\n" + "=" * 60)
print("MISSING COORDINATE ANALYSIS")
print("=" * 60)

missing_coords = places[
    places["latitude"].isna()
    | places["longitude"].isna()
].copy()

print("\nMissing coordinates by category:")
print(
    missing_coords["category"]
    .value_counts()
)

print("\nMissing coordinates by source:")
print(
    missing_coords["source"]
    .value_counts()
)

print("\nMissing coordinates by category + source:")
print(
    missing_coords
    .groupby(
        ["category", "source"],
        dropna=False
    )
    .size()
    .sort_values(ascending=False)
)

print("\nSample places without coordinates:")

print(
    missing_coords[
        [
            "name",
            "category",
            "subcategory",
            "district",
            "city",
            "source",
            "source_file"
        ]
    ]
    .head(30)
    .to_string(index=False)
)

print("\nCoordinate coverage:")

coverage = (
    len(with_coordinates)
    / len(places)
    * 100
)

print(
    f"{coverage:.2f}%"
)