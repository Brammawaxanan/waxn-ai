"""Explainable hybrid ranking for WAXN destinations."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ml.recommendation.semantic_model import (
    DEFAULT_MODEL_PATH,
    DEFAULT_PLACES_PATH,
    load_semantic_model,
)


INTEREST_COLUMNS = {
    "nature": "nature_score",
    "adventure": "adventure_score",
    "history": "history_score",
    "photography": "photography_score",
    "food": "food_score",
    "relaxation": "relaxation_score",
    "family": "family_score",
    "shopping": "shopping_score",
}


def _normalise_preferences(preferences: dict[str, float] | None) -> dict[str, float]:
    return {
        key.lower(): float(np.clip(value, 0.0, 1.0))
        for key, value in (preferences or {}).items()
        if key.lower() in INTEREST_COLUMNS
    }


class HybridRecommender:
    """Rank by learned meaning, explicit interests, quality and diversity."""

    def __init__(
        self,
        places_path: Path = DEFAULT_PLACES_PATH,
        model_path: Path = DEFAULT_MODEL_PATH,
    ) -> None:
        self.places = pd.read_csv(places_path, low_memory=False)
        self.model = load_semantic_model(model_path)
        model_ids = self.model["place_ids"].astype(str)
        place_ids = self.places["place_id"].astype(str).to_numpy()
        if not np.array_equal(model_ids, place_ids):
            raise ValueError("Place data changed after training; retrain the semantic model.")
        self.embeddings = self.model["embeddings"]

    def embed_query(self, query: str) -> np.ndarray:
        tfidf = self.model["vectorizer"].transform([query])
        latent = self.model["svd"].transform(tfidf)
        return self.model["normalizer"].transform(latent)[0]

    def _explicit_scores(
        self, candidates: pd.DataFrame, preferences: dict[str, float]
    ) -> np.ndarray:
        active = [(INTEREST_COLUMNS[key], value) for key, value in preferences.items()]
        if not active:
            return np.full(len(candidates), 0.5)
        values = np.column_stack(
            [
                pd.to_numeric(candidates[column], errors="coerce").fillna(0).to_numpy()
                for column, _ in active
            ]
        )
        weights = np.asarray([weight for _, weight in active], dtype=float)
        if not np.any(weights):
            return np.full(len(candidates), 0.5)
        return np.average(values, axis=1, weights=weights)

    def _bayesian_quality(self, candidates: pd.DataFrame, prior_strength: int = 20) -> np.ndarray:
        rating = pd.to_numeric(candidates["avg_rating"], errors="coerce")
        count = pd.to_numeric(candidates["review_count"], errors="coerce").fillna(0)
        observed = pd.to_numeric(self.places["avg_rating"], errors="coerce")
        global_mean = float(observed.mean()) if observed.notna().any() else 3.5
        shrunk = (count * rating.fillna(global_mean) + prior_strength * global_mean) / (
            count + prior_strength
        )
        # Confidence prevents an unrated place inheriting the full global score.
        confidence = 0.65 + 0.35 * (count / (count + prior_strength))
        return (shrunk / 5.0 * confidence).to_numpy()

    def recommend(
        self,
        request: str,
        *,
        district: str | None = None,
        categories: Iterable[str] | None = None,
        avoid: Iterable[str] | None = None,
        preferences: dict[str, float] | None = None,
        top_n: int = 10,
        diversity: float = 0.12,
    ) -> pd.DataFrame:
        if not request.strip() and not preferences:
            raise ValueError("Provide a natural-language request or at least one interest.")
        if top_n < 1:
            raise ValueError("top_n must be at least 1.")
        diversity = float(np.clip(diversity, 0.0, 0.8))
        preferences = _normalise_preferences(preferences)
        preference_text = " ".join(
            f"{name} " * max(1, round(weight * 3))
            for name, weight in preferences.items()
            if weight > 0
        )
        query = f"{request.strip()} {preference_text}".strip()
        query_vector = self.embed_query(query)

        mask = np.ones(len(self.places), dtype=bool)
        if district:
            mask &= self.places["district"].fillna("").str.casefold().eq(district.casefold())
        if categories:
            allowed = {value.casefold() for value in categories}
            mask &= self.places["category"].fillna("").str.casefold().isin(allowed)
        if avoid:
            searchable = (
                self.places[["name", "subcategory", "feature_text"]]
                .fillna("")
                .astype(str)
                .agg(" ".join, axis=1)
                .str.casefold()
            )
            for term in avoid:
                cleaned = str(term).strip().casefold()
                if cleaned:
                    mask &= ~searchable.str.contains(cleaned, regex=False)
        indices = np.flatnonzero(mask)
        if not len(indices):
            return self.places.iloc[0:0].copy()

        candidates = self.places.iloc[indices].copy()
        semantic = np.clip(self.embeddings[indices] @ query_vector, -1.0, 1.0)
        semantic = (semantic + 1.0) / 2.0
        explicit = self._explicit_scores(candidates, preferences)
        quality = self._bayesian_quality(candidates)
        data_quality = pd.to_numeric(
            candidates["data_quality_score"], errors="coerce"
        ).fillna(0).to_numpy()
        base_score = 0.55 * semantic + 0.20 * explicit + 0.15 * quality + 0.10 * data_quality

        # Maximal marginal relevance balances relevance against near-duplicates.
        selected_local: list[int] = []
        remaining = set(range(len(candidates)))
        while remaining and len(selected_local) < min(top_n, len(candidates)):
            best_index = None
            best_score = -np.inf
            for local_index in remaining:
                redundancy = 0.0
                if selected_local:
                    redundancy = max(
                        float(self.embeddings[indices[local_index]] @ self.embeddings[indices[other]])
                        for other in selected_local
                    )
                mmr = (1.0 - diversity) * base_score[local_index] - diversity * max(0.0, redundancy)
                if mmr > best_score:
                    best_index, best_score = local_index, mmr
            selected_local.append(best_index)
            remaining.remove(best_index)

        result = candidates.iloc[selected_local].copy()
        selected_array = np.asarray(selected_local)
        result["semantic_score"] = semantic[selected_array].round(4)
        result["interest_score"] = explicit[selected_array].round(4)
        result["bayesian_quality_score"] = quality[selected_array].round(4)
        result["recommendation_score"] = base_score[selected_array].round(4)
        result["explanation"] = [
            self._explain(row, preferences) for _, row in result.iterrows()
        ]
        return result.reset_index(drop=True)

    @staticmethod
    def _explain(row: pd.Series, preferences: dict[str, float]) -> str:
        def numeric(value: object) -> float:
            try:
                number = float(value)
                return number if np.isfinite(number) else 0.0
            except (TypeError, ValueError):
                return 0.0

        matches = sorted(
            (
                (name, numeric(row.get(column, 0)) * weight)
                for name, column in INTEREST_COLUMNS.items()
                if (weight := preferences.get(name, 0)) > 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        reasons = [name for name, score in matches[:2] if score > 0]
        reason_text = " and ".join(reasons) if reasons else "your trip description"
        semantic = numeric(row.get("semantic_score"))
        strength = "Strong" if semantic >= 0.58 else "Possible"
        return f"{strength} match for {reason_text}; rating quality is adjusted for review confidence."
