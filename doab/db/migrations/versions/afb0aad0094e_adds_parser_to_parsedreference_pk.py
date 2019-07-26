"""Adds parser to ParsedReference PK

Revision ID: afb0aad0094e
Revises: fc899b721c89
Create Date: 2019-07-26 17:05:51.792311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'afb0aad0094e'
down_revision = 'fc899b721c89'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE parsed_reference DROP CONSTRAINT parsed_reference_pkey CASCADE')
    op.execute('ALTER TABLE parsed_reference ADD PRIMARY KEY (parser,reference_id)')


def downgrade():
    op.execute('ALTER TABLE parsed_reference DROP CONSTRAINT parsed_reference_pkey CASCADE')
    op.execute('ALTER TABLE parsed_reference ADD PRIMARY KEY (reference_id)')
