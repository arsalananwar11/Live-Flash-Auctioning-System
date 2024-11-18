from flask import Flask
from models import db, Users, Auction, AuctionInterest, AuctionWinner
from config import Config
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database
db.init_app(app)
migrate = Migrate(app, db)


@app.route('/')
def index():
    return "Welcome to Flask with RDS!"


@app.route('/users')
def get_users():
    # Fetch all users
    users = Users.query.all()
    # Return user data
    return {"users": [{"user_id": user.user_id, "user_name": user.user_name} for user in users]}


@app.route('/auctions')
def get_auctions():
    # Fetch all auctions
    auctions = Auction.query.all()

    # Return all auction data in JSON format
    return {
        "auctions": [
            {
                "auction_id": auction.auction_id,
                "auction_item": auction.auction_item,
                "base_price": auction.base_price,
                "start_time": auction.start_time.strftime("%Y-%m-%d %H:%M:%S") if auction.start_time else None,
                "end_time": auction.end_time.strftime("%Y-%m-%d %H:%M:%S") if auction.end_time else None,
                "default_time_increment": auction.default_time_increment,
                "default_time_increment_after": auction.default_time_increment_after,
                "auction_desc": auction.auction_desc,
                "is_active": auction.is_active,
                "created_by": auction.created_by,
                "created_on": auction.created_on.strftime("%Y-%m-%d %H:%M:%S") if auction.created_on else None,
                "modified_on": auction.modified_on.strftime("%Y-%m-%d %H:%M:%S") if auction.modified_on else None,
                "stop_snipes_after": auction.stop_snipes_after
            }
            for auction in auctions
        ]
    }


@app.route('/interests')
def get_interests():
    # Fetch all auction interests
    interests = AuctionInterest.query.all()
    # Return interest data
    return {"interests": [{"auction_id": interest.auction.auction_id, "user_id": interest.user.user_id} for interest in interests]}


@app.route('/winners')
def get_winners():
    # Fetch all auction winners
    winners = AuctionWinner.query.all()
    # Return winner data
    return {"winners": [{"auction_id": winner.auction.auction_id, "user_id": winner.user.user_id} for winner in winners]}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't already exist
    app.run(debug=True)
