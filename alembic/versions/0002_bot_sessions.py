import sqlalchemy as sa
from alembic import op

revision = "0002_bot_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_sessions",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("state", sa.String(255)),
        sa.Column("data", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bot_sessions")
