import pandas as pd
from surprise import (
    Dataset,
    Reader,
)  # Importing Surprise library for recommendation systems
from surprise import KNNBasic  # K-Nearest Neighbors for collaborative filtering
from surprise.model_selection import (
    train_test_split,
)  # Splitting dataset for training/testing
from surprise import accuracy  # Accuracy metrics for evaluation
from typing import List, Any
from surprise.dataset import DatasetAutoFolds


def load_data(data_dict: List[dict[str, Any]]):
    """Loads sample dataset and prepares it for Surprise library."""

    # Creating a sample dataset with user_id, product_id, and rating
    df = pd.DataFrame(data_dict)  # Converting dictionary to DataFrame

    # Defining reader with rating scale (1 to 5)
    reader = Reader(rating_scale=(1, 5))

    # Loading data into Surprise dataset format
    data = Dataset.load_from_df(df[["user_id", "product_id", "rating"]], reader)
    return data, df


def train_model(data: DatasetAutoFolds, sim_type="user"):
    """Trains a collaborative filtering model based on user or item similarity."""
    # Splitting dataset into training (80%) and testing (20%)
    trainset, testset = train_test_split(data, test_size=0.2)

    # Setting similarity options for KNN model
    sim_options = {
        "name": "cosine",  # Using cosine similarity
        "user_based": (
            True if sim_type == "user" else False
        ),  # Switching between user-based and item-based CF
    }

    # Initializing KNN-based collaborative filtering model
    model = KNNBasic(sim_options=sim_options)

    # Training the model on the training set
    model.fit(trainset)

    # Making predictions on the test set
    predictions = model.test(testset)

    # Calculating Root Mean Squared Error (RMSE) to evaluate model performance
    rmse = accuracy.rmse(predictions)

    return model, predictions, rmse, trainset


def get_recommendations(model: KNNBasic, df: pd.DataFrame, user_id, n=5):
    """Generates top-N product recommendations for a given user."""
    # Get all unique product IDs
    all_products = df["product_id"].unique()

    # Get products already rated by the user
    rated_products = df[df["user_id"] == user_id]["product_id"].values

    # Find unrated products
    unrated_products = [prod for prod in all_products if prod not in rated_products]

    # Predict ratings for unrated products
    predictions = [
        (prod, model.predict(user_id, prod).est) for prod in unrated_products
    ]

    # Sort by highest predicted rating
    recommendations = sorted(predictions, key=lambda x: x[1], reverse=True)[:n]

    return recommendations


def cf(user_id: str, rating_data: List[dict[str, Any]], top_n=5) -> list[tuple]:
    """A Collaborative Filtering based recommendation system"""

    data, df = load_data(rating_data)

    print("Training User-Based CF...")
    # Train user-based collaborative filtering model
    user_cf_model, user_predictions, user_rmse, _ = train_model(data, sim_type="user")

    # print("\nTraining Item-Based CF...")
    # Train item-based collaborative filtering model
    # item_cf_model, item_predictions, item_rmse, _ = train_model(data, sim_type="item")

    # Get recommendations for a specific user
    recommendations = get_recommendations(user_cf_model, df, user_id, n=top_n)

    return recommendations
