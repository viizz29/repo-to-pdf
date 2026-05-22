from typing import Optional
from datetime import datetime

from app.core.schema import CamelCaseSchema


class SubmitJobDto(CamelCaseSchema):
    url: str


class JobResponseDto(CamelCaseSchema):
    id: int
    user_id: int
    url: str
    file_id: Optional[int]
    finished: bool
    created_at: datetime
    updated_at: datetime
