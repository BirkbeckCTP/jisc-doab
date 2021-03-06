"""Adds Intersection model migration

Revision ID: 3f51db0d3b56
Revises: afb0aad0094e
Create Date: 2019-07-26 18:53:02.987344

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f51db0d3b56'
down_revision = 'afb0aad0094e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('intersection',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('book_id', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['book_id'], ['book.doab_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint('reference_matched_id_fkey', 'reference', type_='foreignkey')
    op.create_foreign_key(None, 'reference', 'intersection', ['matched_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'reference', type_='foreignkey')
    op.create_foreign_key('reference_matched_id_fkey', 'reference', 'book', ['matched_id'], ['doab_id'])
    op.drop_table('intersection')
    # ### end Alembic commands ###
