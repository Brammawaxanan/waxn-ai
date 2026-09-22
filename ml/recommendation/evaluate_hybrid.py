"""Evaluate semantic retrieval using reviews excluded from model training."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ml.recommendation.hybrid_recommender import HybridRecommender
from ml.recommendation.semantic_model import DEFAULT_EVALUATION_PATH


def evaluate() -> dict[str, float | int]:
    recommender = HybridRecommender()
    cases = json.loads(DEFAULT_EVALUATION_PATH.read_text(encoding="utf-8"))
    id_to_index = {
        place_id: index for index, place_id in enumerate(recommender.model["place_ids"])
    }
    reciprocal_ranks = []
    hits_at_5 = []
    hits_at_10 = []
    baseline_reciprocal_ranks = []
    baseline_hits_at_10 = []
    for case in cases:
        target = id_to_index.get(case["place_id"])
        if target is None:
            continue
        category = recommender.places.iloc[target]["category"]
        candidate_indices = np.flatnonzero(
            recommender.places["category"].fillna("").eq(category).to_numpy()
        )
        query = recommender.embed_query(case["query"])
        scores = recommender.embeddings[candidate_indices] @ query
        order = candidate_indices[np.argsort(-scores)]
        rank = int(np.flatnonzero(order == target)[0]) + 1

        # Quality-only ranking is the fair baseline when the old model cannot
        # convert a free-text review into its hand-authored interest vector.
        quality = pd.to_numeric(
            recommender.places.iloc[candidate_indices]["quality_score"], errors="coerce"
        ).fillna(0)
        data_quality = pd.to_numeric(
            recommender.places.iloc[candidate_indices]["data_quality_score"],
            errors="coerce",
        ).fillna(0)
        baseline_scores = 0.6 * quality.to_numpy() + 0.4 * data_quality.to_numpy()
        baseline_order = candidate_indices[np.argsort(-baseline_scores)]
        baseline_rank = int(np.flatnonzero(baseline_order == target)[0]) + 1

        reciprocal_ranks.append(1.0 / rank)
        hits_at_5.append(rank <= 5)
        hits_at_10.append(rank <= 10)
        baseline_reciprocal_ranks.append(1.0 / baseline_rank)
        baseline_hits_at_10.append(baseline_rank <= 10)
    if not reciprocal_ranks:
        raise ValueError("No usable holdout reviews were found.")
    return {
        "evaluation_cases": len(reciprocal_ranks),
        "mean_reciprocal_rank": round(float(np.mean(reciprocal_ranks)), 4),
        "recall_at_5": round(float(np.mean(hits_at_5)), 4),
        "recall_at_10": round(float(np.mean(hits_at_10)), 4),
        "quality_baseline_mrr": round(float(np.mean(baseline_reciprocal_ranks)), 4),
        "quality_baseline_recall_at_10": round(float(np.mean(baseline_hits_at_10)), 4),
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
