from sqlalchemy.orm import Session

from .model import Job
from .worker import start_job_processing


class JobService:
    def submit(self, db: Session, user_id: int, dto):
        job = Job(
            user_id=user_id,
            url=dto.url,
            file_id=None,
            finished=False,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        start_job_processing(job.id)
        return job

    def list_by_user(self, db: Session, user_id: int):
        return (
            db.query(Job)
            .filter(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .all()
        )
