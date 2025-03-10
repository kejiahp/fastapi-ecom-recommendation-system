from fastapi import APIRouter, status
from bson import ObjectId
from datetime import timedelta
from secrets import token_urlsafe
from datetime import datetime

from pymongo import ReturnDocument

from app.core.mailing import (
    send_email,
    request_authcode_email,
    request_code_reset_token,
)
from app.users.user_models import (
    UserModel,
    CreateUserDto,
    LoginDto,
    PublicUserModel,
    LoginUserModel,
    CodeResetTokenDto,
    CodeResetDto,
)
from app.core.db import get_collection, MONGO_COLLECTIONS
from app.core.utils import (
    HTTPMessageException,
    collection_error_msg,
    generate_six_digit_code,
    Message,
)
from app.core.config import settings
from app.core.security import get_code_hash, verify_code, create_access_token


router = APIRouter(prefix="/user")


@router.post("/sign-up", name="sign_up")
async def sign_up(user_dto: CreateUserDto):
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("sign_up", MONGO_COLLECTIONS.USERS.name),
            success=False,
        )

    # generate 6 digit code
    gen_code = str(generate_six_digit_code())

    # covert the generated 6 digit code to a string then hash it
    code_hash = get_code_hash(gen_code)
    user_dto: dict[str, str] = user_dto.model_dump()
    email = user_dto.pop("email")
    user_dto.update({"code_hash": code_hash})

    # check if a user with the same username exists
    if (
        user_with_username := await user_coll.find_one(
            {"username": user_dto["username"]}
        )
    ) is not None:
        raise HTTPMessageException(
            message="A user with this username already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # send auth code to users email
        email_data = request_authcode_email(
            username=user_dto["username"], auth_code=gen_code
        )
        send_email(
            email_to=email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    except Exception as exc:
        print("#### FAILED TO SEND PASSWORD RESET MAIL ####")
        print(exc)
        print("#### FAILED TO SEND PASSWORD RESET MAIL ####")
        raise HTTPMessageException(
            message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # validate user data
    user_model = UserModel(**user_dto)

    # create new user
    new_user = await user_coll.insert_one(
        user_model.model_dump(by_alias=True, exclude=["id"])
    )

    # fetch and return new user
    new_user = await user_coll.find_one({"_id": new_user.inserted_id})
    return Message(
        message="User successfully created",
        status_code=status.HTTP_201_CREATED,
        success=True,
        data=PublicUserModel(**new_user).model_dump(),
    )


@router.post("/sign-in", name="sign_in")
async def sign_in(signin_dto: LoginDto):
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("sign_up", MONGO_COLLECTIONS.USERS.name),
            success=False,
        )
    # find user by username
    if (user := await user_coll.find_one({"username": signin_dto.username})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="A user with this username does not exist",
        )
    # validate users code
    if (verify_code(str(signin_dto.code), user["code_hash"])) == False:
        raise HTTPMessageException(
            message="Invalid authentication code",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    # generate authentication token, expires in 8 days
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_tkn = create_access_token(user.get("id"), expires_delta=access_token_expires)
    # remove sensitive user data
    public_user = UserModel(**user)
    public_user = public_user.model_dump(by_alias=True)
    res = {**public_user, "tkn": access_tkn}
    return Message(
        message="Sign in successful",
        status_code=status.HTTP_200_OK,
        success=True,
        data=LoginUserModel(**res).model_dump(),
    )


@router.post("/request-code-reset-token", name="request_code_reset_token")
async def code_reset_token(crtkn_dto: CodeResetTokenDto):
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("sign_up", MONGO_COLLECTIONS.USERS.name),
            success=False,
        )
    # find user by username
    if (user := await user_coll.find_one({"username": crtkn_dto.username})) is None:
        raise HTTPMessageException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="A user with this username does not exist",
        )
    # generate code reset token
    tkn = token_urlsafe(6)
    try:
        # send code reset token to user via mail
        email_data = request_code_reset_token(token=tkn)
        send_email(
            email_to=crtkn_dto.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    except Exception as exc:
        print("#### FAILED TO CODE RESET TOKEN ####")
        print(exc)
        print("#### FAILED TO CODE RESET TOKEN ####")
        raise HTTPMessageException(
            message=str(exc),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    update_opt = {"code_reset_tkn": tkn, "updated_at": datetime.now()}
    await user_coll.find_one_and_update(
        {"_id": user["_id"]},
        {"$set": update_opt},
        return_document=ReturnDocument.AFTER,
    )
    return Message(
        message="A code reset token as been sent to your email",
        status_code=status.HTTP_200_OK,
        success=True,
    )


@router.post("/code-reset", name="code_reset")
async def code_reset(cr_dto: CodeResetDto):
    user_coll = get_collection(MONGO_COLLECTIONS.USERS)
    if user_coll is None:
        raise HTTPMessageException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=collection_error_msg("sign_up", MONGO_COLLECTIONS.USERS.name),
            success=False,
        )

    # find the user using the reset token
    if (
        user := await user_coll.find_one({"code_reset_tkn": cr_dto.reset_token})
    ) is None:
        raise HTTPMessageException(
            message="A user with this reset token does not exist",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # check if old_code matches with the users current code
    if verify_code(str(cr_dto.old_code), user["code_hash"]) == False:
        raise HTTPMessageException(
            message="The old code and the current user's code do not match",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # hash new code
    new_code = get_code_hash(str(cr_dto.new_code))

    update_opt = {"code_reset_tkn": None, "code_hash": new_code}

    await user_coll.update_one({"_id": user["_id"]}, {"$set": update_opt})

    return Message(
        message="Code successfully changed",
        status_code=status.HTTP_200_OK,
        success=True,
    )
