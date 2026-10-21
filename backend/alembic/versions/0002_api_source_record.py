"""Preserve distinct API award rows that share a procurement case number."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Legacy 0001 uses Base.metadata.create_all, so fresh databases already
    # include current model columns. Existing 0001 databases still need this.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("procurement_cases")}
    if "source_record_id" not in columns:
        op.add_column("procurement_cases", sa.Column("source_record_id", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("procurement_cases", "source_record_id")
