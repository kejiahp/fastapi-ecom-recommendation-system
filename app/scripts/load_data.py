import logging
import json
import asyncio
from pathlib import Path
from typing import Any
import random

from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import collection_error_msg, convert_decimal
from app.core.security import get_code_hash
from app.users.user_models import UserModel
from app.core.constants import Constants
from app.products.product_models import (
    ProductModel,
    CategoryModel,
    ProductRatingModel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_categories():
    """Prefill the database with categories"""
    categories_coll = get_collection(MONGO_COLLECTIONS.CATEGORIES)
    if categories_coll is None:
        raise Exception(
            collection_error_msg("load_categories", MONGO_COLLECTIONS.USERS.name)
        )
    # path to the categories data file
    data_file_path = Path(__file__).parent.parent.parent / "data" / "category.json"

    logger.info(" Loading...")

    with open(data_file_path, "r") as categories:
        categories_obj: list[str] = json.load(categories)
        category_data = [
            CategoryModel(name=i).model_dump(by_alias=True, exclude=["id"])
            for i in categories_obj
        ]
        res = await categories_coll.insert_many(category_data)
        logger.info(f"  {len(res.inserted_ids)} categories created")


async def hash_code_user_model(username: str, code: str):
    """
    Running `get_code_hash` is a slow-blocking function.
    Since, we will be hashing the codes of all the users, this will take alot of time.

    Hence, we offload `get_code_hash` to run on a seperate thread using `run_in_executor`, making it non-blocking.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_code_hash, code)
    return UserModel(
        code_hash=result,
        username=username,
        location=Constants.random_country_generator(),
        age=Constants.random_age_generator(),
        gender=Constants.random_gender_generator(),
    )


async def load_users():
    """Prefill the database with users"""
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise Exception(
            collection_error_msg("load_users", MONGO_COLLECTIONS.USERS.name)
        )
    # path to the user data file
    data_file_path = Path(__file__).parent.parent.parent / "data" / "user.json"

    logger.info(" Loading...")

    with open(data_file_path, "r") as users:
        users_obj: list[dict[str, str]] = json.load(users)
        # creates a list of non-blocking functions (Cooroutines)
        tasks = [hash_code_user_model(i["username"], i["code"]) for i in users_obj]
        # excutes all functions in the list concurrently
        result = await asyncio.gather(*tasks)

        user_data = [i.model_dump(by_alias=True, exclude=["id"]) for i in result]

        res = await user_coll.insert_many(user_data)
        logger.info(f"  {len(res.inserted_ids)} users created")


async def load_products():
    """Prefill the database with products"""
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise Exception(
            collection_error_msg("load_products", MONGO_COLLECTIONS.PRODUCTS.name)
        )
    categories_coll = get_collection(MONGO_COLLECTIONS.CATEGORIES)
    if categories_coll is None:
        raise Exception(
            collection_error_msg("load_products", MONGO_COLLECTIONS.CATEGORIES.name)
        )
    # path to the product data file
    data_file_path = Path(__file__).parent.parent.parent / "data" / "product.json"

    logger.info(" Loading...")

    with open(data_file_path, "r") as products:
        products_obj = json.load(products)
        product_data: list[str, Any] = []

        for i in products_obj:
            category = CategoryModel(
                **await categories_coll.find_one({"name": i["category_name"]})
            )
            product_data.append(
                ProductModel(
                    category_id=category.id,
                    product_name=i["product_name"],
                    product_discount_type=Constants.random_discount_type(),
                    product_description=f"{i["product_description"].strip()}. {i["product_other_description"].strip()}",
                    product_price=i["product_price"],
                    product_discount=i["product_discount"],
                    slug=i["slug"],
                    image_url=i["image_url"],
                ).model_dump(by_alias=True, exclude=["id"])
            )

        # converting all `Decimal` to `Decimal128` so mongodb stops complaining
        product_data = [convert_decimal(i) for i in product_data]

        res = await products_coll.insert_many(product_data)
        logger.info(f"  {len(res.inserted_ids)} products created")


async def load_ratings():
    """Prefill the database with product ratings"""
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise Exception(
            collection_error_msg("load_ratings", MONGO_COLLECTIONS.PRODUCTS.name)
        )

    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise Exception(
            collection_error_msg("load_ratings", MONGO_COLLECTIONS.USERS.name)
        )

    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise Exception(
            collection_error_msg("load_ratings", MONGO_COLLECTIONS.PRODUCT_RATINGS.name)
        )

    logger.info(" Loading...")

    all_users = [doc async for doc in user_coll.find({})]
    all_products = [doc async for doc in products_coll.find({})]

    rating_data: list[ProductRatingModel] = []

    for i in all_users:
        rand_product = random.choice(all_products)
        rand_user = random.choice(all_users)
        rand_rating = Constants.random_rating_generator()

        rating_data.append(
            ProductRatingModel(
                user_id=str(rand_user["_id"]),
                product_id=str(rand_product["_id"]),
                rating=rand_rating,
            ).model_dump(by_alias=True, exclude=["id"])
        )

    res = await product_rating_coll.insert_many(rating_data)
    logger.info(f"  {len(res.inserted_ids)} products rating created")


async def main():
    await load_categories()
    await load_users()
    await load_products()
    await load_ratings()


if __name__ == "__main__":
    asyncio.run(main())

# file execution command
# python -m app.scripts.load_data
