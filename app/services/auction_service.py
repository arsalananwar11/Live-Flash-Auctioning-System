from app.models.db_models import Auction


class AuctionService:
    @staticmethod
    def get_auction(auction_id):
        auction_data = Auction.query.filter_by(auction_id=auction_id).first()

        if not auction_data:
            return None

        return auction_data
