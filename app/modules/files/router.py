from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.core.routing import HashIdRoute
from app.modules.auth.dependencies import get_current_user, get_db
from app.modules.auth.model import User

from .schema import FileResponseDto
from .service import FileService
from app.core.schema import HashIdParam

router = APIRouter(prefix="/v1/files", tags=["files"], route_class=HashIdRoute)
service = FileService()


@router.get("", response_model=list[FileResponseDto])
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user),
):
    return service.list_by_user(db, current_user.id)


@router.get("/{file_id}", response_model=FileResponseDto)
def get_file(
    file_id: HashIdParam,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user),
):
    return service.get_file(db, current_user.id, file_id)
