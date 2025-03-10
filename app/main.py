from fastapi import FastAPI, Request
from fastapi import status
from bson.errors import BSONError

from app.core.config import settings
from app.core.utils import Message
from app.core.db import db
from app.users import user_routes
from starlette.middleware.cors import CORSMiddleware


application: FastAPI = FastAPI()

# Set all CORS enabled origins
if settings.all_cors_origins:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
application.include_router(user_routes.router)


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
