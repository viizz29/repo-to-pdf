from collections.abc import Mapping, Sequence

from hashids import Hashids
from fastapi.responses import JSONResponse

from .config import settings

hashids = Hashids(salt=settings.HASHIDS_SALT, min_length=8)


def _should_encode_key(key: str) -> bool:
    return key == "id" or key.endswith("_id")


def _to_snake_case(key: str) -> str:
    characters: list[str] = []
    for index, character in enumerate(key):
        if character.isupper() and index > 0:
            characters.append("_")
        characters.append(character.lower())
    return "".join(characters)


def _should_decode_key(key: str) -> bool:
    return _should_encode_key(_to_snake_case(key))


def _to_camel_case(key: str) -> str:
    if "_" not in key:
        return key

    first, *rest = key.split("_")
    return first + "".join(part.capitalize() for part in rest)


def encode_ids_in_payload(value):
    if isinstance(value, Mapping):
        transformed = {}
        for key, item in value.items():
            key_str = str(key)
            response_key = _to_camel_case(key_str)

            if _should_decode_key(key_str) and isinstance(item, int) and not isinstance(item, bool):
                transformed[response_key] = hashids.encode(item)
            else:
                transformed[response_key] = encode_ids_in_payload(item)
        return transformed

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [encode_ids_in_payload(item) for item in value]

    return value


def _decode_hashid_value(value):
    if isinstance(value, str):
        decoded = hashids.decode(value)
        if len(decoded) == 1:
            return decoded[0]
    return value


def decode_ids_in_payload(value):
    if isinstance(value, Mapping):
        transformed = {}
        for key, item in value.items():
            key_str = str(key)
            if _should_decode_key(key_str):
                if isinstance(item, Sequence) and not isinstance(
                    item, (str, bytes, bytearray)
                ):
                    transformed[key] = [_decode_hashid_value(entry) for entry in item]
                else:
                    transformed[key] = _decode_hashid_value(item)
            else:
                transformed[key] = decode_ids_in_payload(item)
        return transformed

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [decode_ids_in_payload(item) for item in value]

    return value


class HashIdJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return super().render(encode_ids_in_payload(content))
