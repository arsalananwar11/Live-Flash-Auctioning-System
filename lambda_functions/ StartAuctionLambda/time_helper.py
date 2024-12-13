from datetime import timedelta, datetime

def calculate_remaining_time(end_time_str):
    """
    Calculate the remaining time for an auction given its end time.

    Args:
        end_time_str (str): Auction end time in the format 'YYYY-MM-DD HH:MM:SS'

    Returns:
        str: Remaining time in 'HH:MM:SS' format, or a message if time is up.
    """
    # Parse the end time
    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S+00:00')
    
    # Get the current time
    current_time = datetime.utcnow()  # Use UTC for consistency
    
    # Calculate the difference
    remaining_time = end_time - current_time
    
    # If the auction has ended
    if remaining_time.total_seconds() <= 0:
        return "Auction has ended"
    
    # Format the remaining time as HH:MM:SS
    remaining_timedelta = timedelta(seconds=int(remaining_time.total_seconds()))
    formatted_time = str(remaining_timedelta)

    return formatted_time