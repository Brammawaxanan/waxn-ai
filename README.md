# waxn-ai

WAXN is a Sri Lanka destination recommender and itinerary planner.

## Hybrid ML recommender

The current ML pipeline includes a learned latent-semantic model rather than
depending only on keyword rules. It combines:

- TF-IDF phrase features and truncated SVD latent concepts learned from places
  and matched review text;
- explicit traveller interests;
- Bayesian rating quality, which discounts ratings with very few reviews;
- maximal marginal relevance, which reduces near-duplicate recommendations;
- human-readable reasons and component scores for every result.

Train the model after running the existing data pipeline:

```bash
python -m ml.recommendation.train_semantic_model
```

Evaluate it with reviews that were excluded from model training:

```bash
python -m ml.recommendation.evaluate_hybrid
```

The current deterministic holdout contains 39 usable review queries. Within the
same place category, the semantic model reaches `Recall@10 = 0.5385` and
`MRR = 0.3353`, compared with `0.4103` and `0.2160` for the quality-only
baseline. Treat these as an initial signal, not a production claim, because
review coverage is still narrow.

Example usage:

```python
from ml.recommendation.hybrid_recommender import HybridRecommender

model = HybridRecommender()
recommendations = model.recommend(
    "A quiet family trip with waterfalls and photography, avoiding hard hikes",
    district="Badulla",
    categories=["attraction", "activity"],
    avoid=["hiking", "climbing"],
    preferences={"nature": 1.0, "family": 0.8, "photography": 0.9},
    top_n=10,
)
print(recommendations[["name", "recommendation_score", "explanation"]])
```

The existing `recommend_places`, `recommend_attractions`, `recommend_food`, and
`recommend_hotels` functions automatically use this model when passed a
`request`. `plan_trip_v2` also accepts `request` and `avoid`, so existing Python
planning code can adopt semantic ranking without changing its output format.

The review corpus currently covers only a small number of unique places. For
that reason, the model uses reviews as content instead of claiming to provide
catalogue-wide collaborative filtering. Once the application records enough
impressions, saves, additions and removals, those events can be added as a
learning-to-rank training target.
