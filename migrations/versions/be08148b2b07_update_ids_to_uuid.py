"""Update IDs to UUID

Revision ID: be08148b2b07
Revises: ca03efb65554
Create Date: 2024-11-17 20:53:37.965775

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "be08148b2b07"
down_revision = "ca03efb65554"
branch_labels = None
depends_on = None


def upgrade():
    # Drop foreign key constraints and alter columns
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.drop_constraint("auction_interest_ibfk_1", type_="foreignkey")
        batch_op.drop_constraint("auction_interest_ibfk_2", type_="foreignkey")

    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.drop_constraint("auction_winner_ibfk_1", type_="foreignkey")
        batch_op.drop_constraint("auction_winner_ibfk_2", type_="foreignkey")

    # Alter columns in auction table
    with op.batch_alter_table("auction", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "created_by",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            existing_nullable=False,
        )

    # Alter columns in users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            existing_nullable=False,
        )

    # Alter columns in auction_interest table
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            nullable=False,
        )

    # Alter columns in auction_winner table
    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=mysql.VARCHAR(length=50),
            type_=sa.String(length=36),
            nullable=False,
        )

    # Recreate foreign key constraints
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.create_foreign_key(
            None, "auction", ["auction_id"], ["auction_id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            None, "users", ["user_id"], ["user_id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.create_foreign_key(
            None, "auction", ["auction_id"], ["auction_id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            None, "users", ["user_id"], ["user_id"], ondelete="CASCADE"
        )


def downgrade():
    # Drop foreign key constraints and revert columns
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_constraint(None, type_="foreignkey")

    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_constraint(None, type_="foreignkey")

    # Revert columns in auction table
    with op.batch_alter_table("auction", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "created_by",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            existing_nullable=False,
        )

    # Revert columns in users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            existing_nullable=False,
        )

    # Revert columns in auction_interest table
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            nullable=False,
        )

    # Revert columns in auction_winner table
    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.alter_column(
            "auction_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.String(length=36),
            type_=mysql.VARCHAR(length=50),
            nullable=False,
        )

    # Recreate original foreign key constraints
    with op.batch_alter_table("auction_interest", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "auction_interest_ibfk_1",
            "auction",
            ["auction_id"],
            ["auction_id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "auction_interest_ibfk_2",
            "users",
            ["user_id"],
            ["user_id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("auction_winner", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "auction_winner_ibfk_1",
            "auction",
            ["auction_id"],
            ["auction_id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "auction_winner_ibfk_2",
            "users",
            ["user_id"],
            ["user_id"],
            ondelete="CASCADE",
        )
