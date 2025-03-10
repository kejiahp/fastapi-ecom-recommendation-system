from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from typing import Optional, Union
from datetime import datetime
from bson import ObjectId
from enum import Enum

from app.core.types import PyObjectId


class GenderEnum(str, Enum):
    male = "male"
    female = "female"


class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    code_hash: str
    code_reset_tkn: Union[str, None] = None
    username: str
    location: str
    age: int
    gender: GenderEnum
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class PublicUserModel(BaseModel):
    id: PyObjectId = Field(alias="_id")
    username: str
    location: str
    age: int
    gender: GenderEnum
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LoginUserModel(PublicUserModel):
    tkn: Union[str | None] = None


class CreateUserDto(BaseModel):
    email: str
    username: str
    location: str
    age: int
    gender: GenderEnum


class LoginDto(BaseModel):
    username: str
    code: int

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        if not (100000 <= value <= 999999):
            raise ValueError("code must be a 6-digit number")
        return value


class CodeResetTokenDto(BaseModel):
    username: str
    email: EmailStr


class CodeResetDto(BaseModel):
    new_code: int
    old_code: int
    reset_token: str

    @field_validator("old_code")
    @classmethod
    def validate_old_code(cls, value):
        if not (100000 <= value <= 999999):
            raise ValueError("code must be a 6-digit number")
        return value

    @field_validator("new_code")
    @classmethod
    def validate_new_code(cls, value):
        if not (100000 <= value <= 999999):
            raise ValueError("code must be a 6-digit number")
        return value
