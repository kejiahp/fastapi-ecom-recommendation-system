import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from typing import Any, List, Literal
from decimal import Decimal


def hcbf(
    *,
    product_data: List[dict[str, Any]],
    product_id: str,
    top_n: int = 3,
    user_location: str = None,
    max_price: Decimal = None,
    preferred_category: str = None,
) -> dict[str, Any] | Literal["Product not found."]:
    """
    A Hybrid content-based filtering recommendation system utilizing TF-IDF(Term Frequency-Inverse Document Frequency) and cosine similarity together with demographic based filtering using users country and finally Knowledge based filtering using the specified maximum product price and category

    - Text Similarity: Uses TF-IDF to match product names/descriptions.
    - Category Similarity: Prioritizes products in the same category.
    - Price Similarity: Recommends products in a similar price range.
    - Location Filtering: Ensures only products available near the user are shown.
    - User Preferences: Allows filtering by maximum price and preferred category.

    The weighted combination for text, category and price similarity may vary depending on what the function parameters.
    """

    # Convert dataset to DataFrame
    df = pd.DataFrame(product_data)

    # Normalize price values using Min-Max Scaling, here it will be used to scale prices within the range of 0 - 1
    scaler = MinMaxScaler()
    # `df[["selling_price"]]` returns a DataFrame as opposed to `df["selling_price"]` which returns Series
    df["normalized_price"] = scaler.fit_transform(df[["selling_price"]])

    # Combine text features for better recommendations
    df["text_features"] = df["product_name"] + " " + df["product_description"]

    # Convert text into numerical vectors using TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(df["text_features"])

    # Compute text similarity
    text_similarity = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Compute category similarity (1 if same category, 0 otherwise)
    category_similarity = np.array(
        [
            [
                1 if df.iloc[i]["category_id"] == df.iloc[j]["category_id"] else 0
                for j in range(len(df))
            ]
            for i in range(len(df))
        ]
    )

    # Compute price similarity (inverted absolute difference)
    price_array = df["normalized_price"].values.reshape(-1, 1)
    price_similarity = 1 - np.abs(price_array - price_array.T)

    # dynamically determine the weight for each similarity matrix
    category_weight = 0.3 if preferred_category is not None else 0.0
    price_weight = 0.2 if max_price is not None else 0.0
    text_weight = 1.0 - (category_weight + price_weight)

    # Final similarity score (weighted combination)
    similarity_matrix = (
        (text_weight * text_similarity)
        + (category_weight * category_similarity)
        + (price_weight * price_similarity)
    )

    # Convert to DataFrame
    # similarity_df = pd.DataFrame(similarity_matrix, index=df["id"], columns=df["id"])
    # print(similarity_df)

    result = recommend_products_extra(
        df=df,
        similarity_matrix=similarity_matrix,
        product_id=product_id,
        top_n=top_n,
        user_location=user_location,
        max_price=max_price,
        preferred_category=preferred_category,
    )

    return result


def recommend_products_extra(
    df: pd.DataFrame,
    similarity_matrix: np.ndarray,
    product_id: str,
    top_n=3,
    user_location: str = None,
    max_price: Decimal = None,
    preferred_category: str = None,
):
    """Returns product recommendations based on enhanced similarity filtering."""

    # Validate product ID
    if product_id not in df["id"].values:
        return "Product not found."

    # Get index of the product
    # This checks the dataframe for an entry with the `product_id` then gets the index property and finally the index no.
    product_index = df[df["id"] == product_id].index[0]

    # Get similarity scores
    similarity_scores = list(enumerate(similarity_matrix[product_index]))

    # Sort by highest similarity (excluding itself)
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:]

    # Apply additional filters
    filtered_products = []
    for i, score in similarity_scores:
        product = df.iloc[i]

        # Filter by location
        if user_location and product["location"] != user_location:
            continue

        # Filter by max price
        if max_price and product["selling_price"] > max_price:
            continue

        # Filter by preferred category
        if preferred_category and product["category_id"] != preferred_category:
            continue

        filtered_products.append(
            {
                **product,
                "similarity_score": round(score, 2),
            }
        )

        if len(filtered_products) >= top_n:
            break

    return {"product_id": product_id, "recommended_products": filtered_products}
