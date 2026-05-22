from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, WithJsonSchema, model_validator

from .hashids import decode_ids_in_payload


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelCaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @model_validator(mode="before")
    @classmethod
    def decode_hashids(cls, value):
        return decode_ids_in_payload(value)


def decode_hashid_param(value: Any) -> int:
    decoded = decode_ids_in_payload({"id": value}).get("id")
    if not isinstance(decoded, int):
        raise ValueError("Invalid hashid")
    return decoded


HashIdParam = Annotated[
    int,
    BeforeValidator(decode_hashid_param),
    WithJsonSchema({"type": "string", "example": "jR"}),
]
