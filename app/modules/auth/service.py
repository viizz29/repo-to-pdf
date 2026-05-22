from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token

from .model import User

class AuthService:
    def register(self, db: Session, dto):
        user = User(
            email=dto.email,
            name=dto.name,
            password=hash_password(dto.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def login(self, db: Session, dto):
        user = db.query(User).filter(User.email == dto.email).first()
        if not user or not verify_password(dto.password, user.password):
            return None
        token = create_access_token({"sub": user.email})
        return {
            "token": token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
        }

    def update_password(self, db: Session, user: User, dto):
        if not verify_password(dto.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.password = hash_password(dto.new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"message": "Password updated successfully"}
