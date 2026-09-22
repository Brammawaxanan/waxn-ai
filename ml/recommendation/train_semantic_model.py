"""Command-line entry point for training WAXN's semantic model."""

from ml.recommendation.semantic_model import train_semantic_model


if __name__ == "__main__":
    summary = train_semantic_model()
    print("WAXN semantic model trained")
    print(f"Places: {summary.places}")
    print(f"Places with training reviews: {summary.reviewed_places}")
    print(f"Training reviews: {summary.training_reviews}")
    print(f"Held-out evaluation reviews: {summary.held_out_reviews}")
    print(f"Vocabulary: {summary.vocabulary_size}")
    print(f"Latent dimensions: {summary.latent_dimensions}")
    print(f"Saved: {summary.model_path}")
