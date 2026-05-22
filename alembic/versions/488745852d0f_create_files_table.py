"""create_files_table

Revision ID: 488745852d0f
Revises: 1eed2b42ae59
Create Date: 2026-05-22 12:10:10.800962
"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '488745852d0f'
down_revision = '1eed2b42ae59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    storage_service_enum = sa.Enum(
        "local",
        "azure",
        "aws",
        name="storage_service_enum",
    )

    op.create_table(
        "files",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_service", storage_service_enum, nullable=False),
        sa.Column("identifier", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_files_id"), "files", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_files_id"), table_name="files")
    op.drop_table("files")
    sa.Enum(name="storage_service_enum").drop(op.get_bind(), checkfirst=True)
