from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Identity, String
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, Identity(), primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
