from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Identity, String

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(BigInteger, Identity(), primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    file_id = Column(BigInteger, ForeignKey("files.id"), nullable=True)
    finished = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
