"""appointment identity fields nullable for review staging

Revision ID: 571177d85529
Revises: 0cdbedd5e498
Create Date: 2026-09-07 01:36:58.207164
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '571177d85529'
down_revision: Union[str, None] = '0cdbedd5e498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Batch mode so this applies on both Postgres (native ALTER) and SQLite
    # (table-recreate), keeping local dev/tests runnable against the migration.
    with op.batch_alter_table("appointment") as batch_op:
        batch_op.alter_column("patient_name", existing_type=sa.String(length=255), nullable=True)
        batch_op.alter_column("dob", existing_type=sa.Date(), nullable=True)
        batch_op.alter_column("payer_name", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("appointment") as batch_op:
        batch_op.alter_column("payer_name", existing_type=sa.String(length=255), nullable=False)
        batch_op.alter_column("dob", existing_type=sa.Date(), nullable=False)
        batch_op.alter_column("patient_name", existing_type=sa.String(length=255), nullable=False)
