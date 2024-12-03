const socket = io();

// Join the auction room
socket.emit('join_auction', { auction_id: "{{ auction.auction_id }}" });

// Listen for time updates
socket.on('auction_time_update', (data) => {
    const remainingTime = data.remaining_time;
    const timeElement = document.getElementById('remaining-time');
    timeElement.textContent = `${Math.floor(remainingTime)} seconds`;
});

// Listen for auction end notification
socket.on('auction_ended', (data) => {
    alert(data.message);
    document.getElementById('remaining-time').textContent = "Auction Ended";
});

// Clean up when the user leaves
window.addEventListener('beforeunload', () => {
    socket.emit('leave_auction', { auction_id: "{{ auction.auction_id }}" });
});
