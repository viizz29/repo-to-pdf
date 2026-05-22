"""create local files table

Revision ID: 1eed2b42ae59
Revises: 6a3a5cc8b068
Create Date: 2026-05-22 12:00:10.339325
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '1eed2b42ae59'
down_revision = '6a3a5cc8b068'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "local_files",
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("relative_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_local_files_uuid"), "local_files", ["uuid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_local_files_uuid"), table_name="local_files")
    op.drop_table("local_files")
