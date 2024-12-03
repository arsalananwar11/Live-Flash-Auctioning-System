from datetime import datetime
from app.models.db_models import Auction
from sqlalchemy.orm import joinedload
from flask_socketio import SocketIO, emit, join_room, leave_room

socketio = SocketIO(cors_allowed_origins="*")

class AuctionService:
    @staticmethod
    def get_auction(auction_id):
        auction_data = Auction.query.filter_by(auction_id=auction_id).first()

        if not auction_data:
            return None

        return auction_data

    @staticmethod
    def get_all_auctions():
        auctions = Auction.query.options(
            joinedload(
                Auction.interests
            ),  # Eager load auction interests (users interested)
            joinedload(Auction.winners),  # Eager load auction winners (users who won)
        ).all()

        return auctions

    @staticmethod
    def get_upcoming_auctions():
        auctions = (
            Auction.query.options(
                joinedload(Auction.interests),
                joinedload(Auction.winners),
            )
            .filter(Auction.end_time > datetime.utcnow())
            .all()
        )

        return auctions

    @staticmethod
    def get_my_auctions(user_email):
        auctions = (
            Auction.query.options(
                joinedload(Auction.interests),
                joinedload(Auction.winners),
            )
            .filter(Auction.created_by == user_email)
            .all()
        )

        return auctions

    @staticmethod
    def prepare_auction_data(auctions):
        # Prepare the response data
        auctions_list = []
        for auction in auctions:
            auction_data = {
                "auction_id": auction.auction_id,
                "auction_item": auction.auction_item,
                "base_price": auction.base_price,
                "start_time": auction.start_time,
                "end_time": auction.end_time,
                "default_time_increment": auction.default_time_increment,
                "default_time_increment_before": auction.default_time_increment_before,
                "auction_desc": auction.auction_desc,
                "is_active": auction.is_active,
                "created_by": auction.created_by,
                "created_on": auction.created_on,
                "modified_on": auction.modified_on,
                "stop_snipes_after": auction.stop_snipes_after,
                "interests": [
                    {"user_id": interest.user_id, "user_name": interest.user.user_name}
                    for interest in auction.interests
                ],  # Get interested users
                "winners": [
                    {"user_id": winner.user_id, "user_name": winner.user.user_name}
                    for winner in auction.winners
                ],  # Get winning users
            }
            auctions_list.append(auction_data)

        return auctions_list

@socketio.on('join_auction')
def handle_join_auction(data):
    print("auction joined")
    auction_id = data.get('auction_id')
    user_id = data.get('user_id')  # Optional, if tracking user info

    auction = AuctionService().get_auction(auction_id)
    if not auction:
        emit('error', {'message': 'Auction not found'})
        return

    # Join WebSocket room for this auction
    join_room(auction_id)

    # Calculate remaining time
    now = datetime.utcnow()
    end_time = auction.end_time
    remaining_time = (end_time - now).total_seconds()

    print(f"Remaining Time: {remaining_time}")  # Debugging print statement

    if remaining_time <= 0:
        emit('auction_ended', {'message': 'This auction has ended'})
        return

    # Send the remaining time to the user
    emit('auction_time_update', {'remaining_time': remaining_time}, to=auction_id)


@socketio.on('leave_auction')
def handle_leave_auction(data):
    auction_id = data.get('auction_id')
    leave_room(auction_id)
    emit('user_left', {'message': f'User left auction {auction_id}'}, to=auction_id)

