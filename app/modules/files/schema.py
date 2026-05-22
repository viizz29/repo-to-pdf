from app.core.schema import CamelCaseSchema


class FileResponseDto(CamelCaseSchema):
    id: int
    original_name: str
    mime_type: str
    size: int
    sha256: str
