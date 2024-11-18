class AuctionService:
    @staticmethod
    def get_auction(auction_id):
        auction_data = {
            "auction_id": "A001",
            "auction_item": "Antique Vase",
            "base_price": 250.5,
            "start_time": "1/1/2024 10:00",
            "end_time": "1/1/2024 18:00",
            "default_time_increment": "minutes",
            "default_time_increment_after": "seconds",
            "auction_desc": "A rare 18th century antique vase.",
            "is_active": 1,
            "created_by": "U001",
            "created_on": "1/1/2024 9:00",
            "modified_on": None,
            "stop_snipes_after": 15
        }

        
        
        return auction_data if auction_id == auction_data["auction_id"] else None
    