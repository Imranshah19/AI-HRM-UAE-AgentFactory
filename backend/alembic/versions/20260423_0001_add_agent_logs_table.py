"""add_agent_logs_table

Revision ID: a3f7e9b2c1d4
Revises: 801be01bf93b
Create Date: 2026-04-23 00:01:00.000000+00:00

Creates the agent_logs table for the Agent Factory layer.
This is an append-only audit table — no FKs to existing tables
so it can be added without touching existing schema.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'a3f7e9b2c1d4'
down_revision: Union[str, None] = '801be01bf93b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_logs",

        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),

        # Task identity
        sa.Column("task_id",    sa.String(36),  nullable=False, unique=True),

        # Agent routing
        sa.Column("agent_name", sa.String(64),  nullable=False),
        sa.Column("domain",     sa.String(32),  nullable=False),
        sa.Column("action",     sa.String(64),  nullable=False),

        # Outcome
        sa.Column("status",      sa.String(16),  nullable=False),
        sa.Column("result",      JSONB,           nullable=True),
        sa.Column("duration_ms", sa.Float(),      nullable=True),

        # Context
        sa.Column("tenant_id",              sa.String(64),  nullable=True),
        sa.Column("triggered_by",           sa.String(32),  nullable=False, server_default="api"),
        sa.Column("triggered_by_user_id",   sa.String(36),  nullable=True),

        # AI token metadata
        sa.Column("model_used",     sa.String(64), nullable=True),
        sa.Column("input_tokens",   sa.Integer(),  nullable=True),
        sa.Column("output_tokens",  sa.Integer(),  nullable=True),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index("ix_agent_logs_id",             "agent_logs", ["id"])
    op.create_index("ix_agent_logs_task_id",         "agent_logs", ["task_id"], unique=True)
    op.create_index("ix_agent_logs_agent_name",      "agent_logs", ["agent_name"])
    op.create_index("ix_agent_logs_domain",          "agent_logs", ["domain"])
    op.create_index("ix_agent_logs_status",          "agent_logs", ["status"])
    op.create_index("ix_agent_logs_tenant_id",       "agent_logs", ["tenant_id"])
    op.create_index("ix_agent_logs_domain_action",   "agent_logs", ["domain", "action"])
    op.create_index("ix_agent_logs_tenant_created",  "agent_logs", ["tenant_id", "created_at"])
    op.create_index("ix_agent_logs_status_created",  "agent_logs", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_logs_status_created",  table_name="agent_logs")
    op.drop_index("ix_agent_logs_tenant_created",  table_name="agent_logs")
    op.drop_index("ix_agent_logs_domain_action",   table_name="agent_logs")
    op.drop_index("ix_agent_logs_tenant_id",       table_name="agent_logs")
    op.drop_index("ix_agent_logs_status",          table_name="agent_logs")
    op.drop_index("ix_agent_logs_domain",          table_name="agent_logs")
    op.drop_index("ix_agent_logs_agent_name",      table_name="agent_logs")
    op.drop_index("ix_agent_logs_task_id",         table_name="agent_logs")
    op.drop_index("ix_agent_logs_id",              table_name="agent_logs")
    op.drop_table("agent_logs")
