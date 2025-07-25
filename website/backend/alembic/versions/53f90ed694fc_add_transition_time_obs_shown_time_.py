"""add: transition time_obs_shown, time_action_input

Revision ID: 53f90ed694fc
Revises: 35f09b92a953
Create Date: 2025-07-24 11:42:23.176514

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '53f90ed694fc'
down_revision: str | Sequence[str] | None = '35f09b92a953'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transition', sa.Column('time_obs_shown', sa.DateTime(timezone=True), nullable=True))
    op.add_column('transition', sa.Column('time_action_input', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transition', 'time_action_input')
    op.drop_column('transition', 'time_obs_shown')
    # ### end Alembic commands ###
