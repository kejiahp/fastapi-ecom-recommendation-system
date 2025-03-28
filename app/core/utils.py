from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from typing import Union, Dict, Any
from secrets import randbelow
from bson.decimal128 import Decimal128
from decimal import Decimal


class Message(BaseModel):
    message: str
    status_code: int
    success: bool
    data: Union[Dict[str, Any], list, None] = None


class TokenPayload(BaseModel):
    exp: int
    sub: str


class HTTPMessageException(HTTPException):
    def __init__(
        self,
        status_code,
        message: str,
        success: bool = False,
        json_res=False,
        headers=None,
    ):
        # used in combination with the global exception handler, to determine response format
        self.json_res = json_res
        _detail = Message(
            message=message, status_code=status_code, success=success, data=None
        )
        _detail = _detail.model_dump()
        del _detail["data"]
        super().__init__(status_code, _detail, headers)


def collection_error_msg(func_name: str, collection_name: str) -> str:
    return f"[{func_name}]: Collection with name: {collection_name} was not found."


def generate_six_digit_code():
    return randbelow(900000) + 100000


def convert_decimal(dict_item: dict):
    # This function iterates a dictionary looking for types of Decimal and converts them to Decimal128
    # Embedded dictionaries and lists are called recursively.
    if dict_item is None:
        return None

    for k, v in list(dict_item.items()):
        if isinstance(v, dict):
            convert_decimal(v)
        elif isinstance(v, list):
            for l in v:
                convert_decimal(l)
        elif isinstance(v, Decimal):
            dict_item[k] = Decimal128(str(v))

    return dict_item
