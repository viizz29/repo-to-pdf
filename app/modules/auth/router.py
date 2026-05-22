from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.core.routing import HashIdRoute

from .dependencies import get_current_user, get_db
from .model import User
from .schema import (
    LoginDto,
    LoginResponseDto,
    MessageResponseDto,
    RegisterDto,
    UpdatePasswordDto,
    UserResponseDto,
)
from .service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"], route_class=HashIdRoute)
service = AuthService()


@router.post("/register", response_model=UserResponseDto)
def register(dto: RegisterDto, db: Session = Depends(get_db)):
    return service.register(db, dto)


@router.post("/login", response_model=LoginResponseDto)
def login(dto: LoginDto, db: Session = Depends(get_db)):
    return service.login(db, dto)


@router.patch("/password", response_model=MessageResponseDto)
def update_password(
    dto: UpdatePasswordDto,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user),
):
    return service.update_password(db, current_user, dto)
