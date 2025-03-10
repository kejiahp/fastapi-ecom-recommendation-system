import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import (
    Field,
    AnyUrl,
    BeforeValidator,
    EmailStr,
    field_validator,
    computed_field,
)
from functools import lru_cache
from typing import Any, Literal, Annotated


from urllib.parse import quote_plus
from enum import Enum
from typing import Union


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_USER: str
    MONGODB_PASSWORD: str
    MONGODB_HOST: str = "localhost"
    MONGO_SCHEME: str = "mongodb"
    MONGO_PORT: int = 27017
    MONGODB_DATABASE_NAME: str = "ecom_recommendation_be"

    DEBUG: bool = True
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    SMTP_USER_EMAIL: EmailStr
    SMTP_PASSWORD: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587  # 465
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    EMAILS_FROM_EMAIL: str | None = None
    EMAILS_FROM_NAME: str | None = None

    # apply `parse_cors` before
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MONGODB_URI(self) -> str:
        uri = "%s://%s:%s@%s:%s/%s?authSource=admin&retryWrites=true&w=majority" % (
            self.MONGO_SCHEME,
            quote_plus(self.MONGODB_USER),
            quote_plus(self.MONGODB_PASSWORD),
            self.MONGODB_HOST,
            self.MONGO_PORT,
            self.MONGODB_DATABASE_NAME,
        )
        return uri

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origins).rstrip("/") for origins in self.BACKEND_CORS_ORIGINS]

    @field_validator("DEBUG")
    @classmethod
    def debug_str_to_bool(cls, value: Any):
        if isinstance(value, str):
            if value.lower() in {"true", "1", "yes"}:
                return True
            elif value.lower() in {"false", "0", "no"}:
                return False
            else:
                raise ValueError("Invalid `DEBUG` env")
        # the `bool` pydantic validator will do some type conversions
        return value


@lru_cache
def get_settings():
    return Settings()


settings: Settings = get_settings()
