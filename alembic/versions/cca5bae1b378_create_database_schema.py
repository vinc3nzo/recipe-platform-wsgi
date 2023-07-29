"""Create database schema

Revision ID: cca5bae1b378
Revises: 
Create Date: 2023-07-29 21:09:20.177073

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cca5bae1b378'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bookmarked_recipes',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('recipe_id', sa.Uuid(), nullable=False),
    sa.Column('date_added', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('user_id', 'recipe_id')
    )
    op.create_table('rated_recipes',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('recipe_id', sa.Uuid(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('user_id', 'recipe_id')
    )
    op.create_table('recipes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('date_created', sa.DateTime(), nullable=False),
    sa.Column('date_edited', sa.DateTime(), nullable=False),
    sa.Column('rating', sa.Float(), nullable=False),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('recipes_tags',
    sa.Column('recipe_id', sa.Uuid(), nullable=False),
    sa.Column('tag_id', sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint('recipe_id', 'tag_id')
    )
    op.create_table('tags',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_password',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('hashed_password', sa.LargeBinary(), nullable=False),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=False),
    sa.Column('last_name', sa.String(), nullable=False),
    sa.Column('date_registered', sa.DateTime(), nullable=False),
    sa.Column('role', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')
    op.drop_table('user_password')
    op.drop_table('tags')
    op.drop_table('recipes_tags')
    op.drop_table('recipes')
    op.drop_table('rated_recipes')
    op.drop_table('bookmarked_recipes')
    # ### end Alembic commands ###
