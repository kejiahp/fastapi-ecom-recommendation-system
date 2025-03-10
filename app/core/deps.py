# from bson import ObjectId
# from fastapi.responses import RedirectResponse
# from fastapi import Depends, Cookie, status, Request, HTTPException
# from typing import Annotated, Union, Optional
# import jwt
# from jwt.exceptions import InvalidTokenError
# from pydantic import ValidationError

# from . import settings, security, get_collection, MONGO_COLLECTIONS
# from .utils import HTTPMessageException, TokenPayload, collection_error_msg
# from app.auth.auth_models import UserModel

# TokenFromCookieDep = Annotated[Union[str, None], Cookie()]


# def is_user_authenticated(
#     request: Request, tk: TokenFromCookieDep = None
# ) -> RedirectResponse | None:
#     if tk is not None:
#         try:
#             payload = jwt.decode(tk, settings.SECRET_KEY, security.ALGORITHM)
#             # validate token
#             TokenPayload(**payload)
#             return RedirectResponse(
#                 status_code=status.HTTP_302_FOUND, url=request.url_for("events")
#             )
#         except Exception:
#             return None


# IsUserAuthenticatedDeps = Annotated[
#     Optional[RedirectResponse], Depends(is_user_authenticated)
# ]


# def get_current_user(tk: TokenFromCookieDep = None) -> UserModel:
#     if tk is None:
#         raise HTTPMessageException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             message="Auth token required",
#             success=False,
#         )
#     try:
#         payload = jwt.decode(tk, settings.SECRET_KEY, security.ALGORITHM)
#         token_data = TokenPayload(**payload)
#     except (InvalidTokenError, ValidationError):
#         raise HTTPMessageException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             message="Invalid token",
#             success=False,
#         )

#     users_collection = get_collection(MONGO_COLLECTIONS.USERS)
#     if users_collection is None:
#         raise HTTPMessageException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             message=collection_error_msg(
#                 "get_current_user", MONGO_COLLECTIONS.USERS.name
#             ),
#             success=False,
#         )
#     if (user := users_collection.find_one({"_id": ObjectId(token_data.sub)})) is None:
#         raise HTTPMessageException(
#             message="User does not exist in the system",
#             status_code=status.HTTP_404_NOT_FOUND,
#             success=False,
#         )
#     user = UserModel(**user)
#     if not user.is_active:
#         raise HTTPMessageException(
#             message="Users account is not activated",
#             status_code=status.HTTP_400_BAD_REQUEST,
#             success=False,
#         )
#     return user


# CurrentUserDeps = Annotated[UserModel, Depends(get_current_user)]
