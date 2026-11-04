import sqlalchemy as sa
from alembic import op

revision = "0003_user_activity"
down_revision = "0002_bot_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_activity",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), primary_key=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("user_activity")
