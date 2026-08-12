from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans


BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


def cluster_attractions_by_day(
    attractions,
    days
):

    attractions = attractions.copy()

    attractions = attractions[
        attractions["latitude"].notna()
        &
        attractions["longitude"].notna()
    ].copy()


    if len(attractions) <= days:

        attractions["day_cluster"] = (
            range(
                1,
                len(attractions) + 1
            )
        )

        return attractions


    coordinates = attractions[
        [
            "latitude",
            "longitude"
        ]
    ].values


    model = KMeans(
        n_clusters=days,
        random_state=42,
        n_init=20
    )


    attractions["cluster"] = (
        model.fit_predict(
            coordinates
        )
    )


    # Convert 0-based cluster to Day 1, Day 2...
    attractions["day_cluster"] = (
        attractions["cluster"]
        + 1
    )


    return attractions


if __name__ == "__main__":

    recommendations = pd.read_csv(
        PROCESSED_DIR
        / "waxn_test_recommendations.csv"
    )


    clustered = cluster_attractions_by_day(
        recommendations,
        days=3
    )


    print("=" * 70)
    print("WAXN AI GEOGRAPHIC CLUSTERING")
    print("=" * 70)


    for day in sorted(
        clustered["day_cluster"]
        .unique()
    ):

        print(
            f"\nDAY {day}"
        )

        print("-" * 70)

        day_places = clustered[
            clustered["day_cluster"]
            ==
            day
        ]

        for _, row in day_places.iterrows():

            print(
                row["name"],
                row["latitude"],
                row["longitude"]
            )


    clustered.to_csv(
        PROCESSED_DIR
        / "waxn_clustered_attractions.csv",
        index=False
    )


    print(
        "\nSaved:"
    )

    print(
        "data/processed/waxn_clustered_attractions.csv"
    )