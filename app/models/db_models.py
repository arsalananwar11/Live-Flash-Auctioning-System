import uuid
from flask_sqlalchemy import SQLAlchemy
import pymysql

pymysql.install_as_MySQLdb()

db = SQLAlchemy()


class Users(db.Model):
    __tablename__ = "users"
    user_id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_name = db.Column(db.String(100), nullable=False)


class Auction(db.Model):
    __tablename__ = "auction"
    auction_id = db.Column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    auction_item = db.Column(db.String(100), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    default_time_increment = db.Column(db.Integer, nullable=False)
    default_time_increment_before = db.Column(db.Integer, nullable=False)
    auction_desc = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False)
    created_by = db.Column(db.String(36), nullable=False)
    created_on = db.Column(db.DateTime, nullable=False)
    modified_on = db.Column(db.DateTime, nullable=True)
    stop_snipes_after = db.Column(db.Integer, nullable=False)


class AuctionInterest(db.Model):
    __tablename__ = "auction_interest"
    auction_id = db.Column(
        db.String(36), db.ForeignKey("auction.auction_id"), primary_key=True
    )
    user_id = db.Column(db.String(36), db.ForeignKey("users.user_id"), primary_key=True)

    auction = db.relationship("Auction", backref="interests")
    user = db.relationship("Users", backref="interests")


class AuctionWinner(db.Model):
    __tablename__ = "auction_winner"
    auction_id = db.Column(
        db.String(36), db.ForeignKey("auction.auction_id"), primary_key=True
    )
    user_id = db.Column(db.String(36), db.ForeignKey("users.user_id"), primary_key=True)

    auction = db.relationship("Auction", backref="winners")
    user = db.relationship("Users", backref="winners")
