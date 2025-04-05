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

from pprint import pprint


def load_data(data_dict: List[dict[str, Any]]):
    """Loads sample dataset and prepares it for Surprise library."""
    # Creating a sample dataset with user_id, product_id, and rating
    # data_dict = {
    #     "user_id": [1, 1, 1, 2, 2, 3, 3, 3, 4, 4],
    #     "product_id": [101, 102, 103, 101, 104, 102, 103, 105, 101, 105],
    #     "rating": [5, 3, 4, 4, 5, 2, 4, 5, 3, 4],
    # }
    df = pd.DataFrame(data_dict)  # Converting dictionary to DataFrame

    pprint(df)

    # Defining reader with rating scale (1 to 5)
    # reader = Reader(rating_scale=(1, 5))

    # Loading data into Surprise dataset format
    # data = Dataset.load_from_df(df[['user_id', 'product_id', 'rating']], reader)
    # return data, df


def cf(rating_data: List[dict[str, Any]]):
    """A Collaborative Filtering based recommendation system"""

    load_data(rating_data)
