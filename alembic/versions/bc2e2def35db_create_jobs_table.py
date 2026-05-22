"""create jobs table

Revision ID: bc2e2def35db
Revises: 488745852d0f
Create Date: 2026-05-22 12:14:22.369723
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = 'bc2e2def35db'
down_revision = '488745852d0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=True),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_id"), "jobs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_id"), table_name="jobs")
    op.drop_table("jobs")
