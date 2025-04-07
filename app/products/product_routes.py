from bson import ObjectId
from fastapi import APIRouter, status
from typing import Any
from pprint import pprint
import random

from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import collection_error_msg, HTTPMessageException, Message
from app.core.deps import CurrentUserDep
from app.products.product_models import (
    ProductModel,
    CategoryListModel,
    CategoryModel,
    ProductRatingListModel,
    ProductListModel,
    ProductRatingModel,
    ProductRatingReviewDto,
)
from app.users.user_models import PublicUserModel
from app.core.deps import IsUserAuthenticatedDeps

from app.recommendation_systems.collaborative_filtering import cf
from app.recommendation_systems.content_based import cbf
from app.recommendation_systems.hybrid_content_based import hcbf

router = APIRouter(prefix="/product")


@router.get("/search/", name="search_product_by_name")
async def search_product_by_name(name: str = None):
    """Find product by its name"""
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "search_product_by_name", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    products = [
        doc
        async for doc in products_coll.find(
            {"product_name": {"$regex": name, "$options": "i"}}
        )
    ]
    product_list = ProductListModel(products=products)
    product_list = [
        {**model.model_dump(), "selling_price": model.selling_price}
        for model in product_list.products
    ]
    return Message(
        message="Product search result",
        status_code=status.HTTP_200_OK,
        success=True,
        data={"products": product_list},
    )


@router.get("/all-categories", name="get_all_categories")
async def get_all_categories():
    categories_coll = get_collection(MONGO_COLLECTIONS.CATEGORIES)
    if categories_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_all_categories", MONGO_COLLECTIONS.CATEGORIES.name
            ),
            success=False,
        )

    categories = [doc async for doc in categories_coll.find({})]

    return Message(
        message="All categories",
        status_code=status.HTTP_200_OK,
        success=True,
        data=CategoryListModel(categories=categories).model_dump(),
    )


@router.get("/get-product-by-category/{category_id}", name="get_product_by_category")
async def get_product_by_category(category_id: str):
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "format_homelisting_product", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    by_category = ProductListModel(
        products=[doc async for doc in products_coll.find({"category_id": category_id})]
    )
    by_category = await format_homelisting_product(by_category.model_dump()["products"])

    return Message(
        status_code=status.HTTP_200_OK,
        success=True,
        message="All product filtered by category",
        data=by_category,
    )


@router.post("/add-product-rating", name="add_product_rating")
async def add_product_rating(
    product_rating_dto: ProductRatingReviewDto, current_user: CurrentUserDep
):
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "add_product_rating", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "add_product_rating", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
        )

    if (
        product := await products_coll.find_one(
            {"_id": ObjectId(product_rating_dto.product_id)}
        )
    ) is None:
        raise HTTPMessageException(
            message="This product does not exist", status_code=status.HTTP_404_NOT_FOUND
        )

    if (
        rating_exist := await product_rating_coll.find_one(
            {"user_id": current_user.id, "product_id": product_rating_dto.product_id}
        )
    ) is not None:
        raise HTTPMessageException(
            message="This product as already been reviewed by you",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    product_inserted = await product_rating_coll.insert_one(
        ProductRatingModel(
            user_id=current_user.id,
            product_id=product_rating_dto.product_id,
            rating=product_rating_dto.rating,
        ).model_dump(by_alias=True, exclude=["id"])
    )

    product_rating = await product_rating_coll.find_one(
        {"_id": product_inserted.inserted_id}
    )

    return Message(
        message="Product as been successfully rated",
        status_code=status.HTTP_200_OK,
        success=True,
        data=ProductRatingModel(**product_rating).model_dump(),
    )


@router.get("/home-product-listing")
async def home_product_listing(
    current_user: IsUserAuthenticatedDeps, recent_view: str = None
):

    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "home_product_listing", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "home_product_listing", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
        )

    all_products = tuple(
        [ProductModel(**i).model_dump() async for i in products_coll.find({})]
    )
    response_data = {
        "new_added": [],
        "trending": [],
        "similar_to_recent_view": [],
        "explore": [],
        "same_location": [],
        "age_range": [],
        "might_interest_you": [],
    }

    # NEWLY ADDED PRODUCTS
    new_added_cursor = products_coll.find().sort("created_at", -1).limit(15)
    new_added = await new_added_cursor.to_list(length=15)
    new_added = await format_homelisting_product(
        ProductListModel(products=new_added).model_dump()["products"]
    )
    response_data["new_added"] = new_added

    # TRENDING PRODUCTS (HIGHEST RATED)
    product_rating_list = await get_top_rated_products()
    prod_list = [
        doc
        async for doc in products_coll.find(
            {"_id": {"$in": [ObjectId(i["_id"]) for i in product_rating_list]}}
        )
    ]
    trending = await format_homelisting_product(
        ProductListModel(products=prod_list).model_dump()["products"]
    )
    response_data["trending"] = trending

    # GET PRODUCTS TO USERS MOST RECENTLY VIEWED PRODUCTS
    if recent_view is not None:
        content_recommended_prods = []
        for i in recent_view.split(",")[:3]:
            for j in cbf(product_id=i, top_n=5, product_data=list(all_products))[
                "recommended_products"
            ]:
                item_already_exists = list(
                    filter(
                        lambda product: product["id"] == j["id"],
                        content_recommended_prods,
                    )
                )
                if len(item_already_exists) <= 0:
                    content_recommended_prods.append(j)

        response_data["similar_to_recent_view"] = await format_homelisting_product(
            content_recommended_prods
        )

    # EXPLORE (A RANDOM SELECTION FOR PRODUCTS)
    response_data["explore"] = await format_homelisting_product(
        random.sample(all_products, 15)
    )

    if current_user is not None:
        # GET PRODUCT IN USERS COUNTRY (LOCATION)
        response_data["same_location"] = await format_homelisting_product(
            list(
                filter(
                    lambda product: product["location"] == current_user.location,
                    all_products,
                )
            )[:15]
        )

        # GET PRODUCTS IN USERS AGE RANGE
        response_data["age_range"] = await format_homelisting_product(
            list(
                filter(
                    lambda product: product["max_age_range"] >= current_user.age,
                    all_products,
                )
            )[:15]
        )

        # USERS PERSONAL RECOMMENDATION (USING COLLABORATIVE FILTERING)
        all_ratings = ProductRatingListModel(
            product_ratings=[doc async for doc in product_rating_coll.find({})]
        )

        # COLLABORATIVE FILTERING
        collaborative_recommendations = cf(
            current_user.id, all_ratings.model_dump()["product_ratings"], top_n=15
        )
        prod_list = [
            doc
            async for doc in products_coll.find(
                {
                    "_id": {
                        "$in": [ObjectId(i[0]) for i in collaborative_recommendations]
                    }
                }
            )
        ]
        prod_list = ProductListModel(products=prod_list)
        response_data["might_interest_you"] = await format_homelisting_product(
            prod_list.model_dump()["products"]
        )

    return Message(
        status_code=status.HTTP_200_OK,
        success=True,
        message="Product Listings",
        data=response_data,
    )


@router.get("/get-related-products/{product_id}")
async def get_related_products(
    product_id: str,
    location: str = None,
    max_price: float = None,
    category_id: str = None,
):
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_related_products", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    # get related products using content-based filtering
    products = ProductListModel(products=[doc async for doc in products_coll.find({})])
    products = [
        {**prod.model_dump(), "selling_price": prod.selling_price}
        for prod in products.products
    ]

    results_hcbf = hcbf(
        product_id=product_id,
        product_data=products,
        top_n=10,
        user_location=location,
        max_price=max_price,
        preferred_category=category_id,
    )

    related_products = [
        {**prod.model_dump(), "selling_price": prod.selling_price}
        for prod in ProductListModel(
            products=[
                product
                for product in results_hcbf["recommended_products"]
                if product["id"] != product_id
            ]
        ).products
    ]

    return Message(
        status_code=status.HTTP_200_OK,
        message="Related products",
        success=True,
        data=related_products,
    )


@router.get("/{product_id}", name="get_product_by_id")
async def get_product_by_id(product_id: str):
    """Get a product by its id"""
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_product_by_id", MONGO_COLLECTIONS.PRODUCTS.name
            ),
            success=False,
        )
    categories_coll = get_collection(MONGO_COLLECTIONS.CATEGORIES)
    if categories_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_product_by_id", MONGO_COLLECTIONS.CATEGORIES.name
            ),
            success=False,
        )
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_product_by_id", MONGO_COLLECTIONS.USERS.name
            ),
        )
    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_product_by_id", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
            success=False,
        )

    if (product := await products_coll.find_one({"_id": ObjectId(product_id)})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Product with id: {product_id} does not exist",
        )

    product = ProductModel(**product)

    if (
        category := await categories_coll.find_one(
            {"_id": ObjectId(product.category_id)}
        )
    ) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Category with id: {product.category_id} does not exist",
        )

    category = CategoryModel(**category)

    product_ratings = [
        doc async for doc in product_rating_coll.find({"product_id": product_id})
    ]
    product_ratings = ProductRatingListModel(
        product_ratings=product_ratings
    ).model_dump()

    product_ratings = [
        {
            **rating,
            "user_id": PublicUserModel(
                **(await user_coll.find_one({"_id": ObjectId(rating["user_id"])})),
            ).model_dump(),
        }
        for rating in product_ratings["product_ratings"]
    ]

    return Message(
        message="All categories",
        status_code=status.HTTP_200_OK,
        success=True,
        data={
            **product.model_dump(),
            "category_id": category.model_dump(),
            "selling_price": product.selling_price,
            "product_ratings": product_ratings,
        },
    )


async def format_homelisting_product(
    products_to_format: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """utility function adding the average rating and selling price to a list of products"""
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "format_homelisting_product", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "format_homelisting_product", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
        )

    all_products = []
    for doc in products_to_format:
        product = ProductModel(**doc)
        product_ratings = [
            doc async for doc in product_rating_coll.find({"product_id": product.id})
        ]
        avg_rating = sum(r["rating"] for r in product_ratings) / len(product_ratings)

        all_products.append(
            {
                **product.model_dump(),
                "selling_price": product.selling_price,
                "avg_rating": round(avg_rating, 2),
            }
        )

    return all_products


async def get_top_rated_products(limit=15):
    """Get product with the highest average rating"""
    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_top_rated_products", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
        )

    pipeline = [
        {
            "$group": {
                "_id": "$product_id",
                "average_rating": {"$avg": "$rating"},
                "rating_count": {"$sum": 1},
            }
        },
        {"$sort": {"average_rating": -1}},
        {"$limit": limit},
    ]

    cursor = product_rating_coll.aggregate(pipeline)
    top_products = []
    async for doc in cursor:
        top_products.append(doc)

    return top_products
