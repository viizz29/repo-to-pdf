# =========================
# modules/auth/schema.py
# =========================
from pydantic import ConfigDict

from app.core.schema import CamelCaseSchema, to_camel


class RegisterDto(CamelCaseSchema):
    email: str
    name: str
    password: str


class LoginDto(CamelCaseSchema):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "email": "user1@example.com",
                "password": "password123",
            }
        },
    )

    email: str
    password: str


class UpdatePasswordDto(CamelCaseSchema):
    current_password: str
    new_password: str


class UserResponseDto(CamelCaseSchema):
    id: int
    name: str
    email: str


class LoginResponseDto(CamelCaseSchema):
    token: str
    user: UserResponseDto


class MessageResponseDto(CamelCaseSchema):
    message: str
