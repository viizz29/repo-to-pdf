from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Identity, String, UUID

from app.core.database import Base


class LocalFile(Base):
    __tablename__ = "local_files"

    uuid = Column(UUID, primary_key=True, index=True)
    original_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)
    relative_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class File(Base):
    __tablename__ = "files"

    id = Column(BigInteger, Identity(), primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    storage_service = Column(
        Enum("local", "azure", "aws", name="storage_service_enum"),
        nullable=False,
    )
    identifier = Column(UUID, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
