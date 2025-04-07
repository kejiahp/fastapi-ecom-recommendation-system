from bson import ObjectId
from fastapi.responses import RedirectResponse
from fastapi import Depends, Header, status, Request, HTTPException
from typing import Annotated, Union, Optional
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import HTTPMessageException, TokenPayload, collection_error_msg
from app.users.user_models import UserModel

# TokenFromCookieDep = Annotated[Union[str, None], Cookie()]

TokenFromHeaderDep = Annotated[Union[str, None], Header()]


async def is_user_authenticated(
    authorization: TokenFromHeaderDep = None,
) -> UserModel | None:
    if authorization is None:
        return None
    try:
        payload = jwt.decode(authorization, settings.SECRET_KEY, ALGORITHM)
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        return None

    users_collection = get_collection(MONGO_COLLECTIONS.USERS)
    if users_collection is None:
        raise HTTPMessageException(
            status_code=status.HTTP_403_FORBIDDEN,
            message=collection_error_msg(
                "get_current_user", MONGO_COLLECTIONS.USERS.name
            ),
            success=False,
        )
    if (
        user := await users_collection.find_one({"_id": ObjectId(token_data.sub)})
    ) is None:
        raise HTTPMessageException(
            message="User does not exist in the system",
            status_code=status.HTTP_403_FORBIDDEN,
            success=False,
        )
    user = UserModel(**user)
    return user


IsUserAuthenticatedDeps = Annotated[Optional[UserModel], Depends(is_user_authenticated)]


async def get_current_user(authorization: TokenFromHeaderDep = None) -> UserModel:
    if authorization is None:
        raise HTTPMessageException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Authorization token required",
            success=False,
        )
    try:
        payload = jwt.decode(authorization, settings.SECRET_KEY, ALGORITHM)
        token_data = TokenPayload(**payload)

    except (InvalidTokenError, ValidationError):
        raise HTTPMessageException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Invalid token",
            success=False,
        )

    users_collection = get_collection(MONGO_COLLECTIONS.USERS)
    if users_collection is None:
        raise HTTPMessageException(
            status_code=status.HTTP_403_FORBIDDEN,
            message=collection_error_msg(
                "get_current_user", MONGO_COLLECTIONS.USERS.name
            ),
            success=False,
        )
    if (
        user := await users_collection.find_one({"_id": ObjectId(token_data.sub)})
    ) is None:
        raise HTTPMessageException(
            message="User does not exist in the system",
            status_code=status.HTTP_403_FORBIDDEN,
            success=False,
        )
    user = UserModel(**user)
    return user


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]
