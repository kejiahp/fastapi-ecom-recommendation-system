from bson import ObjectId
from pprint import pprint
from fastapi import APIRouter, status


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
async def home_product_listing():
    product_rating_coll = get_collection(MONGO_COLLECTIONS.PRODUCT_RATINGS)
    if product_rating_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "home_product_listing", MONGO_COLLECTIONS.PRODUCT_RATINGS.name
            ),
        )

    pass


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
        message="All categories",
        status_code=status.HTTP_200_OK,
        success=True,
        data={
            **product.model_dump(),
            "category_id": category.model_dump(),
            "selling_price": product.selling_price,
            **product_ratings.model_dump(),
            "related_products": related_products,
        },
    )
