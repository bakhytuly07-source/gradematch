import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, strict=True, allow_inf_nan=False)


class Error(Schema):
    code: Literal["validation", "auth", "not_found", "unknown"]
    message: str


class LoginInput(Schema):
    email: str
    password: str


class RegisterInput(LoginInput):
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value.strip()):
            raise ValueError("Invalid email")
        return value


class User(Schema):
    id: str
    email: str


class AuthResult(Schema):
    user: User
    access_token: str
    token_type: Literal["bearer"] = "bearer"


Channel = Annotated[float, Field(ge=0, le=1)]


class StyleParams(Schema):
    id: str
    shadow_tint: list[Channel] = Field(alias="shadowTint", min_length=3, max_length=3)
    highlight_tint: list[Channel] = Field(alias="highlightTint", min_length=3, max_length=3)
    base_saturation: float = Field(alias="baseSaturation")


class Adjustments(Schema):
    intensity: float = Field(ge=0, le=100)
    contrast: float = Field(ge=-50, le=50)
    saturation: float = Field(ge=-50, le=50)
    warmth: float = Field(ge=-50, le=50)


class LutSettings(Schema):
    style_params: StyleParams = Field(alias="styleParams")
    adjustments: Adjustments


class SaveLookInput(LutSettings):
    name: str
    thumbnail: str


class RenameLookInput(Schema):
    name: str = Field(pattern=r"\S")


class Look(Schema):
    id: str
    name: str
    style_params: StyleParams
    adjustments: Adjustments
    thumbnail_url: str
    is_favorite: bool
    created_at: int
    updated_at: int


class LutData(Schema):
    size: Literal[33] = 33
    data: list[Channel] = Field(min_length=107811, max_length=107811)
