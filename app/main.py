from fastapi import FastAPI, Request
from fastapi import status

from bson.errors import BSONError
from app.core.config import settings
from app.core.utils import Message
from app.core.db import db


application: FastAPI = FastAPI()


@application.get(
    "/", name="homepage", status_code=status.HTTP_200_OK, response_model=Message
)
async def base_path(request: Request):
    return {
        "message": "Server is up and running",
        "status_code": status.HTTP_200_OK,
        "success": True,
    }


@application.exception_handler(BSONError)
def invalid_objectID_exception_handler(request: Request, exc: BSONError):
    if len(exc.args) > 0 and isinstance(exc.args[0], str):
        msg = exc.args[0]
    return Message(
        message=msg,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        success=False,
    )
