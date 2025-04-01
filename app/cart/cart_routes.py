from fastapi import APIRouter, status
from bson import ObjectId

from app.core.deps import CurrentUserDep
from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import collection_error_msg, HTTPMessageException, Message
from app.cart.cart_models import CartModel, CartItemModel
from app.products.product_models import ProductListModel

router = APIRouter(prefix="/cart")


@router.get("/get-user-cart", name="get_user_cart")
async def get_user_cart(current_user: CurrentUserDep, populate: str = None):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("get_user_cart", MONGO_COLLECTIONS.CARTS.name),
        )
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_user_cart", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        cart_model = CartModel(**{"user_id": current_user.id})
        inserted = await cart_coll.insert_one(
            cart_model.model_dump(by_alias=True, exclude=["id"])
        )
        cart = await cart_coll.find_one({"_id": inserted.inserted_id})
        return Message(
            message="Users cart",
            status_code=status.HTTP_200_OK,
            success=True,
            data=CartModel(**cart).model_dump(),
        )

    else:
        cart = await cart_coll.find_one({"user_id": current_user.id})
        cart = CartModel(**cart).model_dump()
        if populate is None:
            return Message(
                message="Users cart",
                status_code=status.HTTP_200_OK,
                success=True,
                data=cart,
            )
        else:
            product_ids = [ObjectId(i["product_id"]) for i in cart["cart_items"]]
            cart_products = [
                i async for i in products_coll.find({"_id": {"$in": product_ids}})
            ]
            cart_items = [
                {
                    **i.model_dump(),
                    "selling_price": i.selling_price,
                }
                for i in ProductListModel(products=cart_products).products
            ]
            for item in cart["cart_items"]:
                item["product_id"] = [
                    i for i in cart_items if i["id"] == item["product_id"]
                ][0]
            return Message(
                message="Users cart",
                status_code=status.HTTP_200_OK,
                success=True,
                data=cart,
            )


@router.get("/get-cart-total", name="get_cart_total")
async def get_cart_total(current_user: CurrentUserDep):
    """Get the total price of items in users cart"""
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("get_user_cart", MONGO_COLLECTIONS.CARTS.name),
        )

    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_user_cart", MONGO_COLLECTIONS.PRODUCTS.name
            ),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="User does not have a cart"
        )

    product_ids = [ObjectId(i["product_id"]) for i in cart["cart_items"]]
    cart_products = [i async for i in products_coll.find({"_id": {"$in": product_ids}})]

    cart_items = [
        {
            **i.model_dump(),
            "selling_price": i.selling_price,
        }
        for i in ProductListModel(products=cart_products).products
    ]
    for item in cart["cart_items"]:
        item["product_id"] = [i for i in cart_items if i["id"] == item["product_id"]][0]

    sub_total = 0
    for i in cart["cart_items"]:
        sub_total += i["product_id"]["selling_price"] * i["quantity"]
    data = {"sub_total": sub_total, "delivery_fee": 0, "vat": 0}
    return Message(
        message="Cart total", status_code=status.HTTP_200_OK, success=True, data=data
    )


@router.patch("/add-to-cart", name="add_to_cart")
async def add_to_cart(item: CartItemModel, current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("add_to_cart", MONGO_COLLECTIONS.CARTS.name),
        )
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "add_to_cart", MONGO_COLLECTIONS.PRODUCTS.name
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
    return Message(
        message="Item successfully added to cart",
        status_code=status.HTTP_200_OK,
        success=True,
        data=CartModel(**cart).model_dump(),
    )


@router.delete("/remove-from-cart/{product_id}", name="remove_from_cart")
async def remove_from_cart(product_id: str, current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "remove_from_cart", MONGO_COLLECTIONS.CARTS.name
            ),
        )
    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "remove_from_cart", MONGO_COLLECTIONS.PRODUCTS.name
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

    return Message(
        message="Item successfully removed from cart",
        status_code=status.HTTP_200_OK,
        success=True,
        data=CartModel(**cart).model_dump(),
    )


@router.delete("/empty-cart", name="empty_cart")
async def empty_cart(current_user: CurrentUserDep):
    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("empty_cart", MONGO_COLLECTIONS.CARTS.name),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="User does not have a cart"
        )

    await cart_coll.update_one(
        {"user_id": current_user.id}, {"$set": {"cart_items": []}}
    )
    cart["cart_items"] = []

    return Message(
        message="Cart successfully empty",
        status_code=status.HTTP_200_OK,
        success=True,
        data=CartModel(**cart).model_dump(),
    )
