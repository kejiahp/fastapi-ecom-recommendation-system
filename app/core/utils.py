from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from typing import Union, Dict, Any


class Message(BaseModel):
    message: str
    status_code: int
    success: bool
    data: Union[Dict[str, Any], list, None] = None


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
