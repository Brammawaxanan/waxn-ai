"""Train and load WAXN's latent-semantic place model.

The model is deliberately trained from the repository's own catalogue and review
corpus.  TF-IDF captures important words and phrases, while truncated SVD learns
latent concepts (for example, reviews about trails, climbing and viewpoints tend
to occupy a similar region even when they do not share every word).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import Normalizer


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_PLACES_PATH = PROCESSED_DIR / "waxn_final_candidates.csv"
DEFAULT_REVIEWS_PATH = PROCESSED_DIR / "waxn_reviews_matched.csv"
DEFAULT_MODEL_PATH = PROCESSED_DIR / "waxn_semantic_model.joblib"
DEFAULT_EVALUATION_PATH = PROCESSED_DIR / "waxn_semantic_holdout.json"
MODEL_VERSION = 1


@dataclass(frozen=True)
class TrainingSummary:
    places: int
    reviewed_places: int
    training_reviews: int
    held_out_reviews: int
    vocabulary_size: int
    latent_dimensions: int
    model_path: Path


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def _review_text(row: pd.Series) -> str:
    return " ".join(
        part
        for part in (_clean_text(row.get("title")), _clean_text(row.get("text")))
        if part
    )


def _split_reviews(reviews: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Hold out one deterministic review per place for honest retrieval tests."""
    matched = reviews[
        reviews["matched_place_id"].notna() & reviews["text"].notna()
    ].copy()
    matched["review_document"] = matched.apply(_review_text, axis=1)
    matched = matched[matched["review_document"].str.len() >= 40].copy()
    matched["stable_key"] = matched["review_id"].astype(str).map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )
    matched = matched.sort_values(["matched_place_id", "stable_key"])

    holdout_indices: list[int] = []
    holdout: list[dict] = []
    for place_id, group in matched.groupby("matched_place_id", sort=True):
        if len(group) < 2:
            continue
        row = group.iloc[0]
        holdout_indices.append(row.name)
        holdout.append(
            {
                "review_id": str(row["review_id"]),
                "place_id": str(place_id),
                "query": row["review_document"],
            }
        )

    return matched.drop(index=holdout_indices), holdout


def _aggregate_reviews(reviews: pd.DataFrame, max_reviews: int = 25) -> dict[str, str]:
    if reviews.empty:
        return {}

    ranking_columns = [
        column for column in ("matched_place_id", "helpful_votes", "published_date")
        if column in reviews.columns
    ]
    ascending = [True] + [False] * (len(ranking_columns) - 1)
    ranked = reviews.sort_values(ranking_columns, ascending=ascending)
    selected = ranked.groupby("matched_place_id", sort=False).head(max_reviews)
    return (
        selected.groupby("matched_place_id")["review_document"]
        .apply(lambda values: " ".join(values))
        .to_dict()
    )


def _place_document(row: pd.Series, review_text: str) -> str:
    # Repeating the name/category is an intentional field-weighting technique.
    name = _clean_text(row.get("name"))
    category = _clean_text(row.get("category"))
    fields = [
        name,
        name,
        name,
        category,
        category,
        _clean_text(row.get("subcategory")),
        _clean_text(row.get("district")),
        _clean_text(row.get("city")),
        _clean_text(row.get("feature_text")),
        review_text,
    ]
    return " ".join(part for part in fields if part)


def _fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def train_semantic_model(
    places_path: Path = DEFAULT_PLACES_PATH,
    reviews_path: Path = DEFAULT_REVIEWS_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    evaluation_path: Path = DEFAULT_EVALUATION_PATH,
    dimensions: int = 96,
) -> TrainingSummary:
    places = pd.read_csv(places_path, low_memory=False)
    reviews = pd.read_csv(reviews_path, low_memory=False)
    training_reviews, holdout = _split_reviews(reviews)
    review_documents = _aggregate_reviews(training_reviews)

    documents = [
        _place_document(row, review_documents.get(str(row["place_id"]), ""))
        for _, row in places.iterrows()
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.98,
        max_features=30_000,
        sublinear_tf=True,
    )
    tfidf = vectorizer.fit_transform(documents)
    max_dimensions = max(2, min(tfidf.shape) - 1)
    latent_dimensions = min(dimensions, max_dimensions)
    svd = TruncatedSVD(n_components=latent_dimensions, random_state=42)
    normalizer = Normalizer(copy=False)
    embeddings = normalizer.fit_transform(svd.fit_transform(tfidf)).astype(np.float32)

    bundle = {
        "model_version": MODEL_VERSION,
        "data_fingerprint": _fingerprint((places_path, reviews_path)),
        "place_ids": places["place_id"].astype(str).to_numpy(),
        "vectorizer": vectorizer,
        "svd": svd,
        "normalizer": normalizer,
        "embeddings": embeddings,
        "explained_variance": float(svd.explained_variance_ratio_.sum()),
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path, compress=3)
    evaluation_path.write_text(json.dumps(holdout, indent=2), encoding="utf-8")

    return TrainingSummary(
        places=len(places),
        reviewed_places=len(review_documents),
        training_reviews=len(training_reviews),
        held_out_reviews=len(holdout),
        vocabulary_size=len(vectorizer.vocabulary_),
        latent_dimensions=latent_dimensions,
        model_path=model_path,
    )


def load_semantic_model(model_path: Path = DEFAULT_MODEL_PATH) -> dict:
    if not model_path.exists():
        raise FileNotFoundError(
            f"Semantic model not found at {model_path}. "
            "Run `python -m ml.recommendation.train_semantic_model` first."
        )
    bundle = joblib.load(model_path)
    if bundle.get("model_version") != MODEL_VERSION:
        raise ValueError("Semantic model version is incompatible; retrain the model.")
    return bundle

