from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from bson import ObjectId
from enum import Enum

from app.core.types import PyObjectId


class CartItemModel(BaseModel):
    product_id: str
    quantity: int = Field(min=0, max=10)


class CartModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    cart_items: List[CartItemModel] = []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )
