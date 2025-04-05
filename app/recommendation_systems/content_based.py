import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any, List, Literal


def cbf(
    *, product_id: str, top_n: int = 3, product_data: List[dict[str, Any]]
) -> dict[str, Any] | Literal["Product not found."]:
    """
    A content-based filtering recommendation system utilizing TF-IDF(Term Frequency-Inverse Document Frequency) and cosine similarity to measure similarities in products using the product name and product description.

    **IMPORTANT:** This is the patient-zero(initial implementation) of the content-based filtering system, recommendations are purely based on TF-IDF.
    """

    # Convert to DataFrame
    df = pd.DataFrame(product_data)

    # use TF-IDF(Term Frequency-Inverse Document Frequency) vectorization to convert text data into numerical form

    # Combine product name and description for better feature extraction
    df["text_features"] = df["product_name"] + " " + df["product_description"]

    # Convert text into numerical vectors using TF-IDF
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(df["text_features"])

    # Use cosine similarity to measure product similarity

    # Compute cosine similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Convert similarity matrix to DataFrame
    # similarity_df = pd.DataFrame(similarity_matrix, index=df["id"], columns=df["id"])

    # Display similarity matrix
    # print(similarity_df)

    result = recommend_products(
        product_id=product_id,
        top_n=top_n,
        df=df,
        similarity_matrix=similarity_matrix,
    )

    return result


def recommend_products(
    *, product_id: str, df: pd.DataFrame, similarity_matrix: np.ndarray, top_n=3
):
    if product_id not in df["id"].values:
        return "Product not found."

    # Get index of the product
    # This checks the dataframe for an entry with the `product_id` then gets the index property and finally the index no.
    product_index = df[df["id"] == product_id].index[0]

    # Get similarity scores for the product
    similarity_scores = list(enumerate(similarity_matrix[product_index]))

    # Sort products by similarity score (excluding itself)
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[
        1 : top_n + 1
    ]

    # Get recommended products
    # `.iloc` is a property in pandas used to access rows and columns in a DataFrame by integer position.
    recommended_products = [{**df.iloc[i[0]]} for i in similarity_scores]

    return {"product_id": product_id, "recommended_products": recommended_products}
