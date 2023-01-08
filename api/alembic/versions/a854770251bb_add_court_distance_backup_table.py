"""add_court_distance_backup_table

Revision ID: a854770251bb
Revises: 8bc4f7b9396c
Create Date: 2023-01-07 14:43:49.051832

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a854770251bb'
down_revision = '8bc4f7b9396c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('court_distance_backup',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('court_id', sa.Integer(), nullable=True),
    sa.Column('interpreter_id', sa.Integer(), nullable=True),
    sa.Column('court_code', sa.String(), nullable=True),
    sa.Column('court_address', sa.String(), nullable=True),
    sa.Column('interpreter_address', sa.String(), nullable=True),
    sa.Column('distance', sa.Integer(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('court_latitude', sa.Float(), nullable=True),
    sa.Column('court_longitude', sa.Float(), nullable=True),
    sa.Column('interpreter_latitude', sa.Float(), nullable=True),
    sa.Column('interpreter_longitude', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_court_distance_backup_id'), 'court_distance_backup', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_court_distance_backup_id'), table_name='court_distance_backup')
    op.drop_table('court_distance_backup')
    # ### end Alembic commands ###
