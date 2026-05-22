from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .model import File, LocalFile


class FileService:
    def list_by_user(self, db: Session, user_id: int):
        return (
            db.query(
                File.id.label("id"),
                LocalFile.original_name.label("original_name"),
                LocalFile.mime_type.label("mime_type"),
                LocalFile.size.label("size"),
                LocalFile.sha256.label("sha256"),
            )
            .join(LocalFile, File.identifier == LocalFile.uuid)
            .filter(File.user_id == user_id)
            .filter(File.storage_service == "local")
            .order_by(File.created_at.desc())
            .all()
        )

    def get_file(self, db: Session, user_id: int, file_id: int):
        file = (
            db.query(
                File.id.label("id"),
                LocalFile.original_name.label("original_name"),
                LocalFile.mime_type.label("mime_type"),
                LocalFile.size.label("size"),
                LocalFile.sha256.label("sha256"),
            )
            .join(LocalFile, File.identifier == LocalFile.uuid)
            .filter(File.id == file_id)
            .filter(File.user_id == user_id)
            .filter(File.storage_service == "local")
            .first()
        )

        if file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        return file
