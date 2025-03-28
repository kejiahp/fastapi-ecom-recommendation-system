from bson import ObjectId
from pprint import pprint
from fastapi import APIRouter, status


from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import collection_error_msg, HTTPMessageException
from app.products.product_models import (
    ProductModel,
    CategoryListModel,
    CategoryModel,
    ProductRatingListModel,
    ProductListModel,
)

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
    return {"products": product_list}


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

    return CategoryListModel(categories=categories).model_dump()


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
    product_ratings = ProductRatingListModel(product_ratings=product_ratings)

    return {
        **product.model_dump(),
        "category_id": category.model_dump(),
        "selling_price": product.selling_price,
        **product_ratings.model_dump(),
    }
