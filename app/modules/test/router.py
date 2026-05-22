from fastapi import APIRouter, Depends, Security
import os
from sqlalchemy.orm import Session
from app.modules.auth.dependencies import get_current_user, get_db
from app.core.routing import HashIdRoute
from app.modules.auth.model import User

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

router = APIRouter(prefix="/v1/test", tags=["test"], route_class=HashIdRoute)

@router.get("/test1")
def test1():
    return "test1 success"

@router.get("/test2")
def get_persons(db: Session = Depends(get_db), current_user: User = Security(get_current_user),):
    return "test2 success"
