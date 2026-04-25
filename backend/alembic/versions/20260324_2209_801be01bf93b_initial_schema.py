"""initial_schema

Revision ID: 801be01bf93b
Revises: 
Create Date: 2026-03-24 22:09:28.769345+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801be01bf93b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import all models to ensure Base.metadata is fully populated
    import app.models  # noqa: F401
    from app.models.base import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    import app.models  # noqa: F401
    from app.models.base import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
