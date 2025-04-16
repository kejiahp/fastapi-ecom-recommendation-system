from fastapi import APIRouter, status
from bson import ObjectId

from app.products.product_models import ProductModel, ProductListModel
from app.order.order_models import OrderModel, OrderItemModel, OrderListModel
from app.cart.cart_models import CartModel
from app.core.deps import CurrentUserDep
from app.core.db import MONGO_COLLECTIONS, get_collection
from app.core.mailing import send_order_receipt_email, send_email
from app.core.utils import (
    HTTPMessageException,
    collection_error_msg,
    Message,
    convert_decimal,
)

router = APIRouter(prefix="/order")


@router.post("/checkout", name="checkout")
async def checkout(current_user: CurrentUserDep, receipt_email: str = None):
    order_coll = get_collection(MONGO_COLLECTIONS.ORDERS)
    if order_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("checkout", MONGO_COLLECTIONS.ORDERS.name),
        )

    cart_coll = get_collection(MONGO_COLLECTIONS.CARTS)
    if cart_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("checkout", MONGO_COLLECTIONS.CARTS.name),
        )

    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("checkout", MONGO_COLLECTIONS.PRODUCTS.name),
        )

    if (cart := await cart_coll.find_one({"user_id": current_user.id})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_404_NOT_FOUND, message="User does not have a cart"
        )

    if len(cart["cart_items"]) <= 0:
        raise HTTPMessageException(
            message="Your cart is empty, add some items",
            status_code=status.HTTP_400_BAD_REQUEST,
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

    order_items = [
        {"product_id": i["product_id"]["id"], "quantity": i["quantity"]}
        for i in cart["cart_items"]
    ]

    order_dict = OrderModel(
        user_id=current_user.id,
        order_total=sub_total,
        order_item=order_items,
    ).model_dump(by_alias=True, exclude=["id"])

    order_dict = convert_decimal(order_dict)

    order_inserted = await order_coll.insert_one(order_dict)
    order = await order_coll.find_one({"_id": order_inserted.inserted_id})

    # empty users cart
    await cart_coll.update_one(
        {"user_id": current_user.id}, {"$set": {"cart_items": []}}
    )

    products = [
        {
            "name": item["product_id"]["product_name"],
            "image": item["product_id"]["image_url"],
            "price": item["product_id"]["selling_price"],
            "quantity": item["quantity"],
        }
        for item in cart["cart_items"]
    ]

    if receipt_email is not None:
        try:
            # send order confirmation email
            email_data = send_order_receipt_email(
                products=products, total_price=sub_total
            )
            send_email(
                email_to=receipt_email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )

        except Exception as exc:
            print("#### FAILED TO ORDER SUCCESSFUL EMAIL ####")
            print(exc)
            print("#### FAILED TO ORDER SUCCESSFUL EMAIL ####")
            raise HTTPMessageException(
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Message(
        status_code=status.HTTP_200_OK,
        success=True,
        message="Checkout successful",
        data=OrderModel(**order).model_dump(),
    )


@router.get("/get-all-users-orders", name="get_all_users_orders")
async def get_all_users_orders(current_user: CurrentUserDep):
    order_coll = get_collection(MONGO_COLLECTIONS.ORDERS)
    if order_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_all_users_orders", MONGO_COLLECTIONS.ORDERS.name
            ),
        )

    products_coll = get_collection(MONGO_COLLECTIONS.PRODUCTS)
    if products_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg(
                "get_all_users_orders", MONGO_COLLECTIONS.PRODUCTS.name
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

    user_orders = [doc async for doc in order_coll.find({"user_id": current_user.id})]
    user_orders = OrderListModel(orders=user_orders).model_dump()["orders"]

    for i in user_orders:
        for j in i["order_item"]:
            product = ProductModel(
                **await products_coll.find_one({"_id": ObjectId(j["product_id"])})
            )
            rating = await product_rating_coll.find_one(
                {"user_id": current_user.id, "product_id": product.id}
            )
            j["product_id"] = {
                **product.model_dump(),
                "selling_price": product.selling_price,
                "is_rated": True if rating is not None else False,
                "rating_given": rating["rating"] if rating is not None else None,
            }

    return Message(
        status_code=status.HTTP_200_OK,
        message="All user orders",
        success=True,
        data=user_orders,
    )
