from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from bson import ObjectId
from bson.decimal128 import Decimal128
from typing import Union, List
from enum import Enum

from app.core.types import PyObjectId
from app.core.constants import Constants


class DiscountTypeEnum(str, Enum):
    UNIT = "UNIT"
    FIXED = "FIXED"


class CategoryModel(BaseModel):
    id: Union[PyObjectId, None] = Field(alias="_id", default=None)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class CategoryListModel(BaseModel):
    categories: List[CategoryModel]


class ProductModel(BaseModel):
    id: Union[PyObjectId, None] = Field(alias="_id", default=None)
    category_id: str
    product_name: str
    product_description: str
    product_price: Decimal
    product_discount: Decimal
    product_discount_type: DiscountTypeEnum
    product_quantity: int = Field(default=1000)
    slug: str
    image_url: str
    location: str = Field(default_factory=Constants.random_country_generator)
    # represents the highest age of a expected customers
    max_age_range: int = Field(default_factory=Constants.random_age_generator)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    @field_validator("product_price", mode="before")
    @classmethod
    def convert_price_to_decimal128(cls, value):
        if isinstance(value, Decimal128):
            return value.to_decimal()  # Convert Decimal128 → Decimal
        return value  # Return as is if already Decimal

    @field_validator("product_discount", mode="before")
    @classmethod
    def convert_price_discount_to_decimal128(cls, value):
        if isinstance(value, Decimal128):
            return value.to_decimal()  # Convert Decimal128 → Decimal
        return value  # Return as is if already Decimal

    @property
    def selling_price(self) -> Decimal:
        if self.product_discount_type == DiscountTypeEnum.FIXED:
            return self.product_price - self.product_discount
        elif self.product_discount_type == DiscountTypeEnum.UNIT:
            return (
                self.product_price - (self.product_price * self.product_discount) / 100
            )
        return self.product_price


class ProductListModel(BaseModel):
    products: List[ProductModel]


class ProductRatingModel(BaseModel):
    id: Union[PyObjectId, None] = Field(alias="_id", default=None)
    user_id: str
    product_id: str
    rating: int = Field(ge=0, le=5)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class ProductRatingListModel(BaseModel):
    product_ratings: List[ProductRatingModel]


class ProductRatingReviewDto(BaseModel):
    product_id: str
    rating: int = Field(ge=1, le=5)
