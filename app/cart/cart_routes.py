from fastapi import APIRouter, status
from bson import ObjectId

from app.core.deps import CurrentUserDep
from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import collection_error_msg, HTTPMessageException
from app.cart.cart_models import CartModel, CartItemModel

router = APIRouter(prefix="/cart")


@router.get("/get-user-cart", name="get_user_cart")
async def get_user_cart(current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("get_user_cart", MONGO_COLLECTIONS.CARTS.name),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        cart_model = CartModel(**{"user_id": current_user.id})
        inserted = await cart_coll.insert_one(
            cart_model.model_dump(by_alias=True, exclude=["id"])
        )
        cart = await cart_coll.find_one({"_id": inserted.inserted_id})
        return CartModel(**cart).model_dump()

    else:
        cart = await cart_coll.find_one({"user_id": current_user.id})
        return CartModel(**cart).model_dump()


@router.patch("/add-to-cart", name="add_to_cart")
async def add_to_cart(item: CartItemModel, current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "update_user_cart_item", MONGO_COLLECTIONS.CARTS.name
            ),
        )
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_user_cart", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    if (
        product := await products_coll.find_one({"_id": ObjectId(item.product_id)})
    ) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="This product does not exist"
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        cart = CartModel(
            user_id=current_user.id, cart_items=item.model_dump()
        ).model_dump(by_alias=True, exclude=["id"])
        await cart_coll.insert_one(cart)
    else:
        # Check if product exists in cart
        for cart_item in cart["cart_items"]:
            if cart_item["product_id"] == item.product_id:
                cart_item["quantity"] += item.quantity
                break
        else:
            cart["cart_items"].append(item.model_dump())

        await cart_coll.update_one(
            {"user_id": current_user.id}, {"$set": {"cart_items": cart["cart_items"]}}
        )
    return CartModel(**cart).model_dump()


@router.delete("/remove-from-cart/{product_id}", name="update_user_cart_item")
async def update_user_cart_item(product_id: str, current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "update_user_cart_item", MONGO_COLLECTIONS.CARTS.name
            ),
        )
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_user_cart", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    if (product := await products_coll.find_one({"_id": ObjectId(product_id)})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="This product does not exist"
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="User does not have a cart"
        )

    cart["cart_items"] = [
        item for item in cart["cart_items"] if item["product_id"] != product_id
    ]
    await cart_coll.update_one(
        {"user_id": current_user.id}, {"$set": {"cart_items": cart["cart_items"]}}
    )

    return CartModel(**cart).model_dump()


@router.delete("/empty-cart", name="empty-cart")
async def empty_cart(current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "update_user_cart_item", MONGO_COLLECTIONS.CARTS.name
            ),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="User does not have a cart"
        )

    await cart_coll.update_one(
        {"user_id": current_user.id}, {"$set": {"cart_items": []}}
    )
    cart["cart_items"] = []

    return CartModel(**cart).model_dump()
