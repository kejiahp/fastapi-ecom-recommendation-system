from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from bson import ObjectId
from datetime import datetime
from decimal import Decimal
from bson.decimal128 import Decimal128
from enum import Enum

from app.core.constants import Constants
from app.products.product_models import ProductModel
from app.core.types import PyObjectId


class OrderEnum(str, Enum):
    COMPLETED = "COMPLETED"


class OrderItemModel(BaseModel):
    product_id: str | ProductModel
    quantity: int = Field(ge=1, le=100)


class OrderModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_id: str
    order_no: str = Field(default_factory=lambda: f"REF_{Constants.randN(12)}")
    order_total: Decimal
    order_status: OrderEnum = OrderEnum.COMPLETED
    order_item: List[OrderItemModel] = []

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    @field_validator("order_total", mode="before")
    @classmethod
    def convert_price_to_decimal128(cls, value):
        if isinstance(value, Decimal128):
            return value.to_decimal()  # Convert Decimal128 → Decimal
        return value  # Return as is if already Decimal


class OrderListModel(BaseModel):
    orders: List[OrderModel]
