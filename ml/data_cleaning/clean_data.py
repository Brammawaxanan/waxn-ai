from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# ============================================================
# WAXN AI DATA CLEANING PIPELINE
# Wander • Adventure • eXplore • Navigate
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# Sri Lanka approximate coordinate bounds
LAT_MIN = 5.8
LAT_MAX = 10.1

LON_MIN = 79.4
LON_MAX = 82.1


# ============================================================
# RAW FILE LISTS
# ============================================================

ACCOMMODATION_FILES = [

    "Information for Accommodation.csv",

    "Boutique Hotels.xlsx",
    "Boutique Villas.xlsx",
    "Bungalows.xlsx",

    "Classified Hotels( 1-5 Star).xlsx",

    "Guest Houses.xlsx",

    "Heritage Bungalow.xlsx",
    "Heritage Homes.xlsx",

    "Home Stay Units.xlsx",

    "Rented Apartments.xlsx",
    "Rented Homes.xlsx",

    "Tourist Hotels.xlsx",
]


ACTIVITY_FILES = {

    "Spa & Wellness Centers.xlsx": "spa_wellness",

    "Spice Gardens.xlsx": "spice_garden",

    "Water Sports Centers.xlsx": "water_sports",

    "Tourist Shops.xlsx": "tourist_shop",
}


OPTIONAL_FILES = [

    "Places for Travel-Dining-Recreational activities and Information of travel agents.csv",

    "Travel Agents.xlsx",
]


# ============================================================
# BASIC FUNCTIONS
# ============================================================


def clean_column_name(column):

    column = str(column).strip().lower()

    column = column.replace("&", "and")

    column = re.sub(
        r"[^a-z0-9]+",
        "_",
        column
    )

    return column.strip("_")


def normalize_columns(df):

    df = df.copy()

    df.columns = [
        clean_column_name(column)
        for column in df.columns
    ]

    return df


def clean_text(value):

    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "":
        return pd.NA

    # Fix common encoding problems
    replacements = {

        "Â": "",

        "â€™": "'",

        "â€˜": "'",

        "â€œ": '"',

        "â€": '"',

        "â€“": "-",

        "â€”": "-",

        "â€¦": "...",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = unicodedata.normalize(
        "NFKC",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.strip()

    if value == "":
        return pd.NA

    return value


def clean_text_columns(df):

    df = df.copy()

    for column in df.columns:

        if (
            pd.api.types.is_object_dtype(df[column])
            or
            pd.api.types.is_string_dtype(df[column])
        ):

            df[column] = df[column].map(
                clean_text
            )

    return df


# ============================================================
# FLEXIBLE CSV / EXCEL LOADER
# ============================================================


def read_csv_flexible(path):

    encodings = [

        "utf-8",

        "utf-8-sig",

        "cp1252",

        "latin1",
    ]

    for encoding in encodings:

        try:

            return pd.read_csv(
                path,
                encoding=encoding,
                low_memory=False
            )

        except UnicodeDecodeError:

            continue

    return pd.read_csv(
        path,
        low_memory=False
    )


def read_table(path):

    extension = path.suffix.lower()

    if extension == ".csv":

        return read_csv_flexible(path)

    if extension in [
        ".xlsx",
        ".xls"
    ]:

        return pd.read_excel(path)

    raise ValueError(
        f"Unsupported file format: {path}"
    )


# ============================================================
# COLUMN HELPERS
# ============================================================


def find_column(
    df,
    possible_names
):

    for name in possible_names:

        if name in df.columns:

            return name

    return None


def get_text_column(
    df,
    possible_names
):

    column = find_column(
        df,
        possible_names
    )

    if column is None:

        return pd.Series(
            pd.NA,
            index=df.index,
            dtype="string"
        )

    return (
        df[column]
        .astype("string")
        .map(clean_text)
    )


def get_numeric_column(
    df,
    possible_names
):

    column = find_column(
        df,
        possible_names
    )

    if column is None:

        return pd.Series(
            np.nan,
            index=df.index
        )

    return pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# NORMALIZED NAME FOR DUPLICATE DETECTION
# ============================================================


def create_name_key(series):

    return (

        series
        .astype("string")

        .str.lower()

        .str.normalize("NFKD")

        .str.encode(
            "ascii",
            errors="ignore"
        )

        .str.decode("ascii")

        .str.replace(
            r"[^a-z0-9]+",
            " ",
            regex=True
        )

        .str.replace(
            r"\s+",
            " ",
            regex=True
        )

        .str.strip()
    )


# ============================================================
# COORDINATE VALIDATION
# ============================================================


def valid_coordinates(
    latitude,
    longitude
):

    return (

        latitude.between(
            LAT_MIN,
            LAT_MAX
        )

        &

        longitude.between(
            LON_MIN,
            LON_MAX
        )
    )


# ============================================================
# 1. CLEAN OSM POI DATASET
# ============================================================


def clean_osm():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[1] Cleaning OpenStreetMap POIs"
    )

    print(
        "=============================================="
    )

    path = (
        RAW_DIR
        / "points_of_interest.geojson"
    )

    poi = gpd.read_file(path)

    poi = normalize_columns(poi)


    # ----------------------------
    # Coordinate system
    # ----------------------------

    if poi.crs is None:

        poi = poi.set_crs(
            epsg=4326
        )

    else:

        poi = poi.to_crs(
            epsg=4326
        )


    # ----------------------------
    # Remove invalid geometry
    # ----------------------------

    poi = poi[
        poi.geometry.notna()
    ].copy()

    poi = poi[
        ~poi.geometry.is_empty
    ].copy()


    # ----------------------------
    # Create display name
    # ----------------------------

    possible_name_columns = [

        "name_en",

        "name_latin",

        "name",

        "name_ta",

        "name_si",
    ]

    available_names = [

        column

        for column
        in possible_name_columns

        if column
        in poi.columns
    ]


    if available_names:

        poi["display_name"] = (

            poi[
                available_names
            ]

            .bfill(
                axis=1
            )

            .iloc[
                :,
                0
            ]

            .map(
                clean_text
            )
        )

    else:

        poi[
            "display_name"
        ] = pd.NA


    # Remove unnamed locations
    poi = poi[
        poi[
            "display_name"
        ].notna()
    ].copy()


    # ----------------------------
    # Extract latitude longitude
    # ----------------------------

    map_points = (
        poi
        .geometry
        .representative_point()
    )

    poi["longitude"] = (
        map_points.x
    )

    poi["latitude"] = (
        map_points.y
    )


    # ----------------------------
    # Validate coordinates
    # ----------------------------

    coordinate_mask = (
        valid_coordinates(
            poi["latitude"],
            poi["longitude"]
        )
    )

    poi = poi[
        coordinate_mask
    ].copy()


    # ----------------------------
    # OSM categories
    # ----------------------------

    tourism = (

        poi
        .get(
            "tourism",
            pd.Series(
                pd.NA,
                index=poi.index
            )
        )

        .astype("string")

        .str.lower()
    )


    amenity = (

        poi
        .get(
            "amenity",
            pd.Series(
                pd.NA,
                index=poi.index
            )
        )

        .astype("string")

        .str.lower()
    )


    shop = (

        poi
        .get(
            "shop",
            pd.Series(
                pd.NA,
                index=poi.index
            )
        )

        .astype("string")

        .str.lower()
    )


    man_made = (

        poi
        .get(
            "man_made",
            pd.Series(
                pd.NA,
                index=poi.index
            )
        )

        .astype("string")

        .str.lower()
    )


    # ----------------------------
    # Useful categories
    # ----------------------------

    accommodation_types = {

        "hotel",

        "guest_house",

        "hostel",

        "motel",

        "chalet",

        "apartment",

        "camp_site",

        "caravan_site",

        "resort",
    }


    food_types = {

        "restaurant",

        "cafe",

        "fast_food",

        "food_court",

        "ice_cream",

        "bar",

        "pub",
    }


    attraction_types = {

        "attraction",

        "viewpoint",

        "museum",

        "gallery",

        "zoo",

        "theme_park",

        "aquarium",

        "artwork",

        "information",
    }


    activity_types = {

        "spa",

        "swimming_pool",

        "cinema",

        "theatre",

        "arts_centre",

        "nightclub",
    }


    useful_man_made = {

        "lighthouse",

        "tower",

        "pier",

        "bridge",

        "observatory",
    }


    poi["category"] = "other"


    poi.loc[
        tourism.isin(
            accommodation_types
        ),
        "category"
    ] = "accommodation"


    poi.loc[
        amenity.isin(
            food_types
        ),
        "category"
    ] = "food"


    poi.loc[
        tourism.isin(
            attraction_types
        ),
        "category"
    ] = "attraction"


    poi.loc[
        amenity.isin(
            activity_types
        ),
        "category"
    ] = "activity"


    poi.loc[
        (
            shop.notna()
            &
            ~shop.isin(
                [
                    "yes",
                    "no",
                    "nan",
                    "<na>"
                ]
            )
        ),
        "category"
    ] = "shopping"


    poi.loc[
        man_made.isin(
            useful_man_made
        ),
        "category"
    ] = "attraction"


    # Only useful travel POIs
    poi = poi[
        poi["category"]
        != "other"
    ].copy()


    # ----------------------------
    # Subcategory
    # ----------------------------

    poi["subcategory"] = pd.NA


    for column in [

        "tourism",

        "amenity",

        "shop",

        "man_made"
    ]:

        if column in poi.columns:

            mask = (

                poi[
                    "subcategory"
                ].isna()

                &

                poi[
                    column
                ].notna()
            )

            poi.loc[
                mask,
                "subcategory"
            ] = (

                poi
                .loc[
                    mask,
                    column
                ]

                .astype(
                    "string"
                )
            )


    # ----------------------------
    # Location fields
    # ----------------------------

    poi["city"] = (

        get_text_column(

            poi,

            [
                "addr_city",
                "adm4_name",
                "adm3_name"
            ]
        )
    )


    poi["district"] = (

        get_text_column(

            poi,

            [
                "adm2_name"
            ]
        )
    )


    poi["province"] = (

        get_text_column(

            poi,

            [
                "adm1_name"
            ]
        )
    )


    poi[
        "opening_hours"
    ] = (

        get_text_column(

            poi,

            [
                "opening_hours"
            ]
        )
    )


    poi[
        "source"
    ] = "openstreetmap"


    poi[
        "source_file"
    ] = path.name


    poi[
        "name_key"
    ] = (

        create_name_key(
            poi[
                "display_name"
            ]
        )
    )


    # ----------------------------
    # Keep useful fields
    # ----------------------------

    columns = [

        "id",

        "display_name",

        "name_key",

        "category",

        "subcategory",

        "tourism",

        "amenity",

        "shop",

        "man_made",

        "opening_hours",

        "city",

        "district",

        "province",

        "latitude",

        "longitude",

        "source",

        "source_file",
    ]


    columns = [

        column

        for column
        in columns

        if column
        in poi.columns
    ]


    poi = poi[
        columns
    ].copy()


    poi = poi.rename(

        columns={

            "id":
            "source_id",

            "display_name":
            "name"
        }
    )


    # ----------------------------
    # Remove exact duplicates
    # ----------------------------

    poi = poi.drop_duplicates(

        subset=[

            "name_key",

            "category",

            "district",

            "latitude",

            "longitude"
        ],

        keep="first"
    )


    output = (
        CLEAN_DIR
        / "poi_clean.csv"
    )


    poi.to_csv(
        output,
        index=False
    )


    print(
        f"OSM cleaned POIs: "
        f"{len(poi):,}"
    )


    print(
        "\nCategory counts:"
    )


    print(
        poi[
            "category"
        ].value_counts()
    )


    return poi


# ============================================================
# 2. ACCOMMODATION
# ============================================================


def standardize_accommodation(
    raw_df,
    source_file
):

    df = normalize_columns(
        raw_df
    )

    df = clean_text_columns(
        df
    )


    output = pd.DataFrame(
        index=df.index
    )


    output["name"] = (

        get_text_column(

            df,

            [
                "name",

                "hotel_name",

                "property_name",

                "establishment_name",

                "accommodation_name"
            ]
        )
    )


    output["type"] = (

        get_text_column(

            df,

            [
                "type",

                "category",

                "accommodation_type",

                "hotel_type"
            ]
        )
    )


    output["address"] = (

        get_text_column(

            df,

            [
                "address",

                "postal_address",

                "location",

                "addr_full"
            ]
        )
    )


    output["district"] = (

        get_text_column(

            df,

            [
                "district",

                "district_name"
            ]
        )
    )


    output["city"] = (

        get_text_column(

            df,

            [
                "city",

                "town",

                "aga_division"
            ]
        )
    )


    output["grade"] = (

        get_text_column(

            df,

            [
                "grade",

                "classification",

                "star_grade",

                "star_rating",

                "class"
            ]
        )
    )


    output["rooms"] = (

        get_numeric_column(

            df,

            [
                "rooms",

                "no_of_rooms",

                "number_of_rooms",

                "room_count"
            ]
        )
    )


    output["latitude"] = (

        get_numeric_column(

            df,

            [
                "latitude",

                "lat"
            ]
        )
    )


    output["longitude"] = (

        get_numeric_column(

            df,

            [
                "longitude",

                "longitude_",

                "lon",

                "lng",

                "long"
            ]
        )
    )


    output["telephone"] = (

        get_text_column(

            df,

            [
                "telephone",

                "phone",

                "contact_no",

                "contact_number",

                "tel"
            ]
        )
    )


    output["email"] = (

        get_text_column(

            df,

            [
                "email",

                "email_address"
            ]
        )
    )


    output["website"] = (

        get_text_column(

            df,

            [
                "website",

                "web",

                "url"
            ]
        )
    )


    # Type fallback from filename

    file_type = (

        source_file

        .replace(
            ".xlsx",
            ""
        )

        .replace(
            ".csv",
            ""
        )

        .lower()

        .replace(
            " ",
            "_"
        )
    )


    output[
        "type"
    ] = (

        output[
            "type"
        ]

        .fillna(
            file_type
        )
    )


    output[
        "source"
    ] = "official_tourism"


    output[
        "source_file"
    ] = source_file


    output = output[
        output[
            "name"
        ].notna()
    ].copy()


    output[
        "name_key"
    ] = (

        create_name_key(
            output[
                "name"
            ]
        )
    )


    return output


def clean_accommodations():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[2] Cleaning accommodation datasets"
    )

    print(
        "=============================================="
    )


    datasets = []


    for filename in ACCOMMODATION_FILES:

        path = (
            RAW_DIR
            / filename
        )


        if not path.exists():

            print(
                f"WARNING: "
                f"{filename} not found"
            )

            continue


        try:

            raw = read_table(
                path
            )


            cleaned = (
                standardize_accommodation(

                    raw,

                    filename
                )
            )


            datasets.append(
                cleaned
            )


            print(

                f"{filename}: "
                f"{len(cleaned):,} rows"
            )


        except Exception as error:

            print(

                f"ERROR reading "
                f"{filename}: "
                f"{error}"
            )


    if not datasets:

        return pd.DataFrame()


    accommodation = pd.concat(

        datasets,

        ignore_index=True,

        sort=False
    )


    # ----------------------------
    # Score record quality
    # ----------------------------

    accommodation[
        "valid_coordinates"
    ] = (

        valid_coordinates(

            accommodation[
                "latitude"
            ],

            accommodation[
                "longitude"
            ]
        )
    )


    useful_columns = [

        "type",

        "address",

        "district",

        "city",

        "grade",

        "rooms",

        "latitude",

        "longitude",

        "telephone",

        "email",

        "website"
    ]


    accommodation[
        "completeness"
    ] = (

        accommodation[
            useful_columns
        ]

        .notna()

        .sum(
            axis=1
        )
    )


    accommodation[
        "coordinate_score"
    ] = (

        accommodation[
            "valid_coordinates"
        ]

        .astype(int)
    )


    # ----------------------------
    # Duplicate key
    # ----------------------------

    accommodation[
        "district_key"
    ] = (

        accommodation[
            "district"
        ]

        .astype(
            "string"
        )

        .fillna("")

        .str.lower()

        .str.strip()
    )


    accommodation[
        "duplicate_key"
    ] = (

        accommodation[
            "name_key"
        ]

        .fillna("")

        +

        "|"

        +

        accommodation[
            "district_key"
        ]
    )


    # Prefer best data
    accommodation = (

        accommodation

        .sort_values(

            by=[

                "duplicate_key",

                "coordinate_score",

                "completeness"
            ],

            ascending=[

                True,

                False,

                False
            ]
        )
    )


    # ----------------------------
    # Merge duplicates
    # ----------------------------

    merged = []


    merge_columns = [

        "type",

        "address",

        "district",

        "city",

        "grade",

        "rooms",

        "latitude",

        "longitude",

        "telephone",

        "email",

        "website"
    ]


    for _, group in accommodation.groupby(

        "duplicate_key",

        dropna=False

    ):

        best = (
            group.iloc[0]
            .copy()
        )


        for column in merge_columns:

            if pd.isna(
                best[
                    column
                ]
            ):

                values = (

                    group[
                        column
                    ]

                    .dropna()
                )

                if not values.empty:

                    best[
                        column
                    ] = values.iloc[0]


        best[
            "all_source_files"
        ] = (

            " | ".join(

                sorted(

                    set(

                        group[
                            "source_file"
                        ]

                        .dropna()

                        .astype(str)
                    )
                )
            )
        )


        merged.append(
            best
        )


    accommodation = pd.DataFrame(
        merged
    )


    accommodation = (

        accommodation

        .drop(

            columns=[

                "valid_coordinates",

                "completeness",

                "coordinate_score",

                "district_key",

                "duplicate_key"
            ],

            errors="ignore"
        )

        .reset_index(
            drop=True
        )
    )


    accommodation.insert(

        0,

        "accommodation_id",

        [

            f"ACC{i:06d}"

            for i
            in range(
                1,
                len(accommodation) + 1
            )
        ]
    )


    accommodation.to_csv(

        CLEAN_DIR
        / "accommodations_clean.csv",

        index=False
    )


    print(

        "\nFinal accommodation records:",

        len(accommodation)
    )


    return accommodation


# ============================================================
# 3. RESTAURANTS
# ============================================================


def clean_restaurants():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[3] Cleaning restaurants"
    )

    print(
        "=============================================="
    )


    path = (
        RAW_DIR
        / "Restaurants.xlsx"
    )


    if not path.exists():

        print(
            "Restaurants.xlsx not found"
        )

        return pd.DataFrame()


    df = read_table(
        path
    )


    df = normalize_columns(
        df
    )


    df = clean_text_columns(
        df
    )


    result = pd.DataFrame(
        index=df.index
    )


    result["name"] = (

        get_text_column(

            df,

            [

                "name",

                "restaurant_name",

                "establishment_name"
            ]
        )
    )


    result["address"] = (

        get_text_column(

            df,

            [

                "address",

                "postal_address",

                "location"
            ]
        )
    )


    result["district"] = (

        get_text_column(

            df,

            [

                "district",

                "district_name"
            ]
        )
    )


    result["city"] = (

        get_text_column(

            df,

            [

                "city",

                "town",

                "location"
            ]
        )
    )


    result["grade"] = (

        get_text_column(

            df,

            [

                "grade",

                "classification",

                "class"
            ]
        )
    )


    result["cuisine"] = (

        get_text_column(

            df,

            [

                "cuisine",

                "cuisine_type",

                "food_type"
            ]
        )
    )


    result["latitude"] = (

        get_numeric_column(

            df,

            [
                "latitude",
                "lat"
            ]
        )
    )


    result["longitude"] = (

        get_numeric_column(

            df,

            [
                "longitude",

                "lon",

                "lng",

                "long"
            ]
        )
    )


    result["telephone"] = (

        get_text_column(

            df,

            [

                "telephone",

                "phone",

                "contact_no",

                "contact_number",

                "tel"
            ]
        )
    )


    result["email"] = (

        get_text_column(

            df,

            [
                "email",

                "email_address"
            ]
        )
    )


    result["website"] = (

        get_text_column(

            df,

            [
                "website",

                "web",

                "url"
            ]
        )
    )


    result[
        "source"
    ] = "official_tourism"


    result[
        "source_file"
    ] = "Restaurants.xlsx"


    result = result[
        result[
            "name"
        ].notna()
    ].copy()


    result[
        "name_key"
    ] = (

        create_name_key(
            result[
                "name"
            ]
        )
    )


    result[
        "district_key"
    ] = (

        result[
            "district"
        ]

        .astype("string")

        .fillna("")

        .str.lower()

        .str.strip()
    )


    result[
        "duplicate_key"
    ] = (

        result[
            "name_key"
        ]

        .fillna("")

        +

        "|"

        +

        result[
            "district_key"
        ]
    )


    result = (

        result

        .drop_duplicates(

            subset=[
                "duplicate_key"
            ],

            keep="first"
        )

        .drop(

            columns=[

                "district_key",

                "duplicate_key"
            ]
        )

        .reset_index(
            drop=True
        )
    )


    result.insert(

        0,

        "restaurant_id",

        [

            f"RES{i:06d}"

            for i
            in range(
                1,
                len(result) + 1
            )
        ]
    )


    result.to_csv(

        CLEAN_DIR
        / "restaurants_clean.csv",

        index=False
    )


    print(

        "Restaurant records:",

        len(result)
    )


    return result


# ============================================================
# 4. ACTIVITY DATASETS
# ============================================================


def clean_activity_file(
    filename,
    category
):

    path = (
        RAW_DIR
        / filename
    )


    df = read_table(
        path
    )


    df = normalize_columns(
        df
    )


    df = clean_text_columns(
        df
    )


    result = pd.DataFrame(
        index=df.index
    )


    result["name"] = (

        get_text_column(

            df,

            [

                "name",

                "center_name",

                "centre_name",

                "shop_name",

                "establishment_name",

                "garden_name"
            ]
        )
    )


    result[
        "category"
    ] = category


    result["address"] = (

        get_text_column(

            df,

            [

                "address",

                "postal_address",

                "location"
            ]
        )
    )


    result["district"] = (

        get_text_column(

            df,

            [

                "district",

                "district_name"
            ]
        )
    )


    result["city"] = (

        get_text_column(

            df,

            [

                "city",

                "town",

                "location"
            ]
        )
    )


    result["latitude"] = (

        get_numeric_column(

            df,

            [
                "latitude",

                "lat"
            ]
        )
    )


    result["longitude"] = (

        get_numeric_column(

            df,

            [

                "longitude",

                "lon",

                "lng",

                "long"
            ]
        )
    )


    result["telephone"] = (

        get_text_column(

            df,

            [

                "telephone",

                "phone",

                "contact_no",

                "contact_number",

                "tel"
            ]
        )
    )


    result["email"] = (

        get_text_column(

            df,

            [
                "email",

                "email_address"
            ]
        )
    )


    result["website"] = (

        get_text_column(

            df,

            [

                "website",

                "web",

                "url"
            ]
        )
    )


    result[
        "source"
    ] = "official_tourism"


    result[
        "source_file"
    ] = filename


    result = result[

        result[
            "name"
        ].notna()

    ].copy()


    result[
        "name_key"
    ] = (

        create_name_key(

            result[
                "name"
            ]
        )
    )


    return result


def clean_activities():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[4] Cleaning activities"
    )

    print(
        "=============================================="
    )


    datasets = []


    for filename, category in ACTIVITY_FILES.items():


        path = (
            RAW_DIR
            / filename
        )


        if not path.exists():

            print(

                f"WARNING: "
                f"{filename} missing"
            )

            continue


        try:


            cleaned = (

                clean_activity_file(

                    filename,

                    category
                )
            )


            datasets.append(
                cleaned
            )


            print(

                filename,

                len(cleaned)
            )


        except Exception as error:


            print(

                "ERROR:",

                filename,

                error
            )


    if not datasets:

        return pd.DataFrame()


    result = pd.concat(

        datasets,

        ignore_index=True,

        sort=False
    )


    result[
        "district_key"
    ] = (

        result[
            "district"
        ]

        .astype("string")

        .fillna("")

        .str.lower()

        .str.strip()
    )


    result[
        "duplicate_key"
    ] = (

        result[
            "name_key"
        ]

        .fillna("")

        +

        "|"

        +

        result[
            "category"
        ]

        +

        "|"

        +

        result[
            "district_key"
        ]
    )


    result = (

        result

        .drop_duplicates(

            subset=[
                "duplicate_key"
            ]
        )

        .drop(

            columns=[

                "district_key",

                "duplicate_key"
            ]
        )

        .reset_index(
            drop=True
        )
    )


    result.insert(

        0,

        "activity_id",

        [

            f"ACT{i:06d}"

            for i
            in range(
                1,
                len(result) + 1
            )
        ]
    )


    result.to_csv(

        CLEAN_DIR
        / "activities_clean.csv",

        index=False
    )


    print(

        "\nActivity records:",

        len(result)
    )


    return result


# ============================================================
# 5. REVIEWS
# ============================================================


def clean_reviews():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[5] Cleaning Reviews"
    )

    print(
        "=============================================="
    )


    path = (
        RAW_DIR
        / "Reviews.csv"
    )


    if not path.exists():

        return pd.DataFrame()


    reviews = read_csv_flexible(
        path
    )


    reviews = normalize_columns(
        reviews
    )


    reviews = clean_text_columns(
        reviews
    )


    if "rating" in reviews.columns:

        reviews[
            "rating"
        ] = (

            pd.to_numeric(

                reviews[
                    "rating"
                ],

                errors="coerce"
            )
        )


        reviews = reviews[

            reviews[
                "rating"
            ]

            .between(
                1,
                5
            )

            |

            reviews[
                "rating"
            ].isna()

        ].copy()


    if "helpful_votes" in reviews.columns:

        reviews[
            "helpful_votes"
        ] = (

            pd.to_numeric(

                reviews[
                    "helpful_votes"
                ],

                errors="coerce"
            )

            .fillna(0)
        )


    # ----------------------------
    # Dates
    # ----------------------------

    for column in [
    "travel_date",
    "published_date"
]:

        if column in reviews.columns:

            reviews[column] = pd.to_datetime(
                reviews[column],
                errors="coerce",
                utc=True,
                format="mixed"
            )


    if "travel_date" in reviews.columns:

        reviews["travel_year"] = (

            reviews["travel_date"].dt.year

        )

        reviews["travel_month"] = (

            reviews["travel_date"].dt.month

        )


    # ----------------------------
    # Remove empty reviews
    # ----------------------------

    if "text" in reviews.columns:


        reviews[
            "text"
        ] = (

            reviews[
                "text"
            ]

            .map(
                clean_text
            )
        )


        reviews = reviews[

            reviews[
                "text"
            ].notna()

        ].copy()


    # ----------------------------
    # Location key
    # ----------------------------

    if (
        "location_name"
        in reviews.columns
    ):


        reviews[
            "location_name_key"
        ] = (

            create_name_key(

                reviews[
                    "location_name"
                ]
            )
        )


    # ----------------------------
    # Remove duplicates
    # ----------------------------

    duplicate_columns = [

        column

        for column in [

            "user_id",

            "location_name",

            "text"

        ]

        if column
        in reviews.columns
    ]


    if duplicate_columns:

        reviews = (

            reviews

            .drop_duplicates(

                subset=
                duplicate_columns,

                keep=
                "first"
            )
        )


    reviews = reviews.reset_index(
        drop=True
    )


    reviews.insert(

        0,

        "review_id",

        [

            f"REV{i:07d}"

            for i
            in range(
                1,
                len(reviews) + 1
            )
        ]
    )


    reviews.to_csv(

        CLEAN_DIR
        / "reviews_clean.csv",

        index=False
    )


    print(

        "Clean reviews:",

        len(reviews)
    )


    return reviews


# ============================================================
# 6. OPTIONAL FILE INSPECTION
# ============================================================


def inspect_optional_files():

    print(
        "\n"
        "=============================================="
    )

    print(
        "[6] Optional datasets"
    )

    print(
        "=============================================="
    )


    records = []


    for filename in OPTIONAL_FILES:


        path = (
            RAW_DIR
            / filename
        )


        if not path.exists():

            continue


        try:


            df = read_table(
                path
            )


            print(

                filename,

                df.shape
            )


            records.append({

                "file":

                filename,

                "rows":

                len(df),

                "columns":

                len(
                    df.columns
                ),

                "column_names":

                " | ".join(

                    map(
                        str,
                        df.columns
                    )
                )
            })


        except Exception as error:


            print(

                "ERROR:",

                filename,

                error
            )


    pd.DataFrame(
        records
    ).to_csv(

        CLEAN_DIR
        / "optional_reference_inventory.csv",

        index=False
    )


# ============================================================
# 7. BUILD MASTER WAXN PLACES
# ============================================================


def build_master_places(

    poi,

    accommodations,

    restaurants,

    activities

):

    print(
        "\n"
        "=============================================="
    )

    print(
        "[7] Building WAXN Master Places"
    )

    print(
        "=============================================="
    )


    datasets = []


    # ----------------------------
    # OSM
    # ----------------------------

    if not poi.empty:


        osm = pd.DataFrame()


        osm["name"] = (
            poi["name"]
        )


        osm[
            "name_key"
        ] = (

            poi[
                "name_key"
            ]
        )


        osm[
            "category"
        ] = (

            poi[
                "category"
            ]
        )


        osm[
            "subcategory"
        ] = (

            poi[
                "subcategory"
            ]
        )


        osm[
            "district"
        ] = (

            poi[
                "district"
            ]
        )


        osm[
            "city"
        ] = (

            poi[
                "city"
            ]
        )


        osm[
            "province"
        ] = (

            poi[
                "province"
            ]
        )


        osm[
            "latitude"
        ] = (

            poi[
                "latitude"
            ]
        )


        osm[
            "longitude"
        ] = (

            poi[
                "longitude"
            ]
        )


        osm[
            "opening_hours"
        ] = (

            poi[
                "opening_hours"
            ]
        )


        osm[
            "source"
        ] = (

            poi[
                "source"
            ]
        )


        osm[
            "source_file"
        ] = (

            poi[
                "source_file"
            ]
        )


        datasets.append(
            osm
        )


    # ----------------------------
    # Accommodation
    # ----------------------------

    if not accommodations.empty:


        acc = pd.DataFrame()


        acc["name"] = (
            accommodations[
                "name"
            ]
        )


        acc[
            "name_key"
        ] = (

            accommodations[
                "name_key"
            ]
        )


        acc[
            "category"
        ] = "accommodation"


        acc[
            "subcategory"
        ] = (

            accommodations[
                "type"
            ]
        )


        acc[
            "district"
        ] = (

            accommodations[
                "district"
            ]
        )


        acc[
            "city"
        ] = (

            accommodations[
                "city"
            ]
        )


        acc[
            "province"
        ] = pd.NA


        acc[
            "latitude"
        ] = (

            accommodations[
                "latitude"
            ]
        )


        acc[
            "longitude"
        ] = (

            accommodations[
                "longitude"
            ]
        )


        acc[
            "opening_hours"
        ] = pd.NA


        acc[
            "source"
        ] = (

            accommodations[
                "source"
            ]
        )


        acc[
            "source_file"
        ] = (

            accommodations[
                "all_source_files"
            ]
        )


        datasets.append(
            acc
        )


    # ----------------------------
    # Restaurants
    # ----------------------------

    if not restaurants.empty:


        food = pd.DataFrame()


        food[
            "name"
        ] = (

            restaurants[
                "name"
            ]
        )


        food[
            "name_key"
        ] = (

            restaurants[
                "name_key"
            ]
        )


        food[
            "category"
        ] = "food"


        food[
            "subcategory"
        ] = (

            restaurants[
                "cuisine"
            ]
        )


        food[
            "district"
        ] = (

            restaurants[
                "district"
            ]
        )


        food[
            "city"
        ] = (

            restaurants[
                "city"
            ]
        )


        food[
            "province"
        ] = pd.NA


        food[
            "latitude"
        ] = (

            restaurants[
                "latitude"
            ]
        )


        food[
            "longitude"
        ] = (

            restaurants[
                "longitude"
            ]
        )


        food[
            "opening_hours"
        ] = pd.NA


        food[
            "source"
        ] = (

            restaurants[
                "source"
            ]
        )


        food[
            "source_file"
        ] = (

            restaurants[
                "source_file"
            ]
        )


        datasets.append(
            food
        )


    # ----------------------------
    # Activities
    # ----------------------------

    if not activities.empty:


        activity = pd.DataFrame()


        activity[
            "name"
        ] = (

            activities[
                "name"
            ]
        )


        activity[
            "name_key"
        ] = (

            activities[
                "name_key"
            ]
        )


        activity[
            "category"
        ] = "activity"


        activity[
            "subcategory"
        ] = (

            activities[
                "category"
            ]
        )


        activity[
            "district"
        ] = (

            activities[
                "district"
            ]
        )


        activity[
            "city"
        ] = (

            activities[
                "city"
            ]
        )


        activity[
            "province"
        ] = pd.NA


        activity[
            "latitude"
        ] = (

            activities[
                "latitude"
            ]
        )


        activity[
            "longitude"
        ] = (

            activities[
                "longitude"
            ]
        )


        activity[
            "opening_hours"
        ] = pd.NA


        activity[
            "source"
        ] = (

            activities[
                "source"
            ]
        )


        activity[
            "source_file"
        ] = (

            activities[
                "source_file"
            ]
        )


        datasets.append(
            activity
        )


    # ----------------------------
    # Combine
    # ----------------------------

    master = pd.concat(

        datasets,

        ignore_index=True,

        sort=False
    )


    master = master[

        master[
            "name"
        ].notna()

    ].copy()


    master[
        "name_key"
    ] = (

        create_name_key(

            master[
                "name"
            ]
        )
    )


    # ----------------------------
    # Quality score
    # ----------------------------

    master[
        "valid_coordinates"
    ] = (

        valid_coordinates(

            master[
                "latitude"
            ],

            master[
                "longitude"
            ]
        )
    )


    quality_columns = [

        "subcategory",

        "district",

        "city",

        "latitude",

        "longitude",

        "opening_hours"
    ]


    master[
        "completeness"
    ] = (

        master[
            quality_columns
        ]

        .notna()

        .sum(
            axis=1
        )
    )


    # Official tourism data gets
    # higher priority when duplicate
    master[
        "source_priority"
    ] = np.where(

        master[
            "source"
        ]

        .astype("string")

        .eq(
            "official_tourism"
        ),

        2,

        1
    )


    master[
        "district_key"
    ] = (

        master[
            "district"
        ]

        .astype("string")

        .fillna("")

        .str.lower()

        .str.strip()
    )


    master[
        "duplicate_key"
    ] = (

        master[
            "name_key"
        ]

        .fillna("")

        +

        "|"

        +

        master[
            "category"
        ]

        +

        "|"

        +

        master[
            "district_key"
        ]
    )


    master = (

        master

        .sort_values(

            by=[

                "duplicate_key",

                "valid_coordinates",

                "source_priority",

                "completeness"
            ],

            ascending=[

                True,

                False,

                False,

                False
            ]
        )
    )


    # ----------------------------
    # Merge duplicate sources
    # ----------------------------

    merged = []


    for _, group in master.groupby(

        "duplicate_key",

        dropna=False

    ):


        best = (

            group
            .iloc[0]
            .copy()
        )


        fields = [

            "subcategory",

            "district",

            "city",

            "province",

            "latitude",

            "longitude",

            "opening_hours"
        ]


        for field in fields:


            if pd.isna(
                best[field]
            ):


                values = (

                    group[
                        field
                    ]

                    .dropna()
                )


                if not values.empty:


                    best[
                        field
                    ] = (

                        values.iloc[0]
                    )


        best[
            "all_sources"
        ] = (

            " | ".join(

                sorted(

                    set(

                        group[
                            "source"
                        ]

                        .dropna()

                        .astype(str)
                    )
                )
            )
        )


        best[
            "all_source_files"
        ] = (

            " | ".join(

                sorted(

                    set(

                        group[
                            "source_file"
                        ]

                        .dropna()

                        .astype(str)
                    )
                )
            )
        )


        merged.append(
            best
        )


    master = pd.DataFrame(
        merged
    )


    master = (

        master

        .drop(

            columns=[

                "valid_coordinates",

                "completeness",

                "source_priority",

                "district_key",

                "duplicate_key"
            ],

            errors="ignore"
        )

        .reset_index(
            drop=True
        )
    )


    master.insert(

        0,

        "place_id",

        [

            f"PLC{i:07d}"

            for i
            in range(
                1,
                len(master) + 1
            )
        ]
    )


    master.to_csv(

        PROCESSED_DIR
        / "waxn_places.csv",

        index=False
    )


    print(

        "\nFinal WAXN places:",

        len(master)
    )


    print(
        "\nFinal categories:"
    )


    print(

        master[
            "category"
        ]

        .value_counts()
    )


    return master


# ============================================================
# CLEANING REPORT
# ============================================================


def save_report(

    poi,

    accommodation,

    restaurants,

    activities,

    reviews,

    master

):


    report = pd.DataFrame([


        {

            "dataset":
            "poi_clean",

            "rows":
            len(poi),

            "file":
            "data/cleaned/poi_clean.csv"
        },


        {

            "dataset":
            "accommodations_clean",

            "rows":
            len(accommodation),

            "file":
            "data/cleaned/accommodations_clean.csv"
        },


        {

            "dataset":
            "restaurants_clean",

            "rows":
            len(restaurants),

            "file":
            "data/cleaned/restaurants_clean.csv"
        },


        {

            "dataset":
            "activities_clean",

            "rows":
            len(activities),

            "file":
            "data/cleaned/activities_clean.csv"
        },


        {

            "dataset":
            "reviews_clean",

            "rows":
            len(reviews),

            "file":
            "data/cleaned/reviews_clean.csv"
        },


        {

            "dataset":
            "waxn_places",

            "rows":
            len(master),

            "file":
            "data/processed/waxn_places.csv"
        }

    ])


    report.to_csv(

        CLEAN_DIR
        / "cleaning_report.csv",

        index=False
    )


    print(
        "\n"
        "============================================================"
    )

    print(
        "WAXN AI DATA CLEANING COMPLETE"
    )

    print(
        "============================================================"
    )


    print(

        report.to_string(
            index=False
        )
    )


    print(
        "============================================================"
    )


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":


    print(
        "============================================================"
    )

    print(
        "WAXN AI DATA CLEANING PIPELINE"
    )

    print(
        "Wander • Adventure • eXplore • Navigate"
    )

    print(
        "============================================================"
    )


    print(
        "\nRaw folder:"
    )

    print(
        RAW_DIR
    )


    print(
        "\nClean folder:"
    )

    print(
        CLEAN_DIR
    )


    print(
        "\nProcessed folder:"
    )

    print(
        PROCESSED_DIR
    )


    # Run cleaning

    poi = clean_osm()


    accommodation = (
        clean_accommodations()
    )


    restaurants = (
        clean_restaurants()
    )


    activities = (
        clean_activities()
    )


    reviews = (
        clean_reviews()
    )


    inspect_optional_files()


    master = (

        build_master_places(

            poi,

            accommodation,

            restaurants,

            activities
        )
    )


    save_report(

        poi,

        accommodation,

        restaurants,

        activities,

        reviews,

        master
    )