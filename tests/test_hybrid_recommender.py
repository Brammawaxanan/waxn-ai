import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ml.recommendation.hybrid_recommender import HybridRecommender
from ml.recommendation.semantic_model import train_semantic_model


class HybridRecommenderTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        directory = Path(self.temp_dir.name)
        self.places_path = directory / "places.csv"
        self.reviews_path = directory / "reviews.csv"
        self.model_path = directory / "model.joblib"
        self.holdout_path = directory / "holdout.json"
        places = pd.DataFrame(
            [
                self.place("P1", "Silver Waterfall", "waterfall nature swimming", 0.9, 0.5),
                self.place("P2", "Jungle Hiking Trail", "forest hiking adventure", 0.8, 1.0),
                self.place("P3", "Ancient Temple", "heritage temple history", 0.1, 0.1),
                self.place("P4", "Mountain View", "mountain scenic photography", 0.8, 0.5),
                self.place("P5", "Family Garden", "garden family relaxing", 0.8, 0.1),
                self.place("P6", "City Museum", "museum heritage history", 0.1, 0.1),
            ]
        )
        places.to_csv(self.places_path, index=False)
        reviews = pd.DataFrame(
            [
                self.review("R1", "P1", "Beautiful water and a peaceful natural pool"),
                self.review("R2", "P1", "A wonderful waterfall surrounded by green forest"),
                self.review("R3", "P2", "A difficult climb and exciting forest trail"),
                self.review("R4", "P2", "Excellent hiking route for adventurous travellers"),
            ]
        )
        reviews.to_csv(self.reviews_path, index=False)
        train_semantic_model(
            self.places_path,
            self.reviews_path,
            self.model_path,
            self.holdout_path,
            dimensions=4,
        )
        self.recommender = HybridRecommender(self.places_path, self.model_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def place(place_id, name, text, nature, adventure):
        return {
            "place_id": place_id,
            "name": name,
            "category": "attraction",
            "subcategory": text,
            "district": "Test",
            "city": "Test City",
            "avg_rating": 4.5,
            "review_count": 10,
            "data_quality_score": 0.9,
            "nature_score": nature,
            "adventure_score": adventure,
            "history_score": 1.0 if "history" in text else 0.0,
            "photography_score": 1.0 if "photography" in text else 0.0,
            "food_score": 0.0,
            "relaxation_score": 1.0 if "relaxing" in text else 0.0,
            "family_score": 1.0 if "family" in text else 0.0,
            "shopping_score": 0.0,
            "feature_text": f"{name} {text}",
        }

    @staticmethod
    def review(review_id, place_id, text):
        return {
            "review_id": review_id,
            "matched_place_id": place_id,
            "title": "Travel review",
            "text": text,
            "helpful_votes": 1,
            "published_date": "2025-01-01",
        }

    def test_natural_language_query_ranks_relevant_place(self):
        result = self.recommender.recommend(
            "I want a waterfall and a peaceful natural pool",
            district="Test",
            top_n=3,
            diversity=0,
        )
        self.assertEqual(result.iloc[0]["place_id"], "P1")
        self.assertIn("semantic_score", result.columns)
        self.assertIn("explanation", result.columns)

    def test_preferences_affect_ranking(self):
        result = self.recommender.recommend(
            "outdoor trip",
            district="Test",
            preferences={"adventure": 1.0},
            top_n=6,
            diversity=0,
        )
        p2 = result.index[result["place_id"] == "P2"][0]
        p3 = result.index[result["place_id"] == "P3"][0]
        self.assertLess(p2, p3)

    def test_avoid_terms_remove_unsuitable_places(self):
        result = self.recommender.recommend(
            "outdoor adventure",
            district="Test",
            avoid=["hiking"],
            top_n=6,
            diversity=0,
        )
        self.assertNotIn("P2", set(result["place_id"]))

    def test_training_creates_unseen_review_holdout(self):
        holdout = json.loads(self.holdout_path.read_text(encoding="utf-8"))
        self.assertEqual(len(holdout), 2)
        self.assertEqual({case["place_id"] for case in holdout}, {"P1", "P2"})

    def test_rejects_empty_request(self):
        with self.assertRaises(ValueError):
            self.recommender.recommend("   ")


if __name__ == "__main__":
    unittest.main()
