from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.core.routing import HashIdRoute
from app.modules.auth.dependencies import get_current_user, get_db
from app.modules.auth.model import User

from .schema import JobResponseDto, SubmitJobDto
from .service import JobService

router = APIRouter(prefix="/v1/jobs", tags=["jobs"], route_class=HashIdRoute)
service = JobService()


@router.post("", response_model=JobResponseDto)
def submit_job(
    dto: SubmitJobDto,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user),
):
    return service.submit(db, current_user.id, dto)


@router.get("", response_model=list[JobResponseDto])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user),
):
    return service.list_by_user(db, current_user.id)
