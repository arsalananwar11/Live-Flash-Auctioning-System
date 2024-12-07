const remainingTimeElement = document.getElementById("remaining-time");
const errorMessageElement = document.getElementById("error-message");
const bidButtonsDiv = document.querySelector('.bid-buttons-container');

export class AuctionWebSocket {
  constructor(websocketUrl, auctionId, userId, userName) {
    this.websocketUrl = websocketUrl;
    this.auctionId = auctionId;
    this.userId = userId;
    this.userName = userName;
    this.socket = null;
    this.topBid = 0;
    this.connectionId = null; // Store the connection ID received from the server
  }

  connect() {
    this.socket = new WebSocket(
      `${this.websocketUrl}?auction_id=${this.auctionId}&user_id=${this.userId}`
    );

    this.socket.onopen = () => {
      console.log("WebSocket connection established.");
      this.sendMessage("join", {
        auction_id: this.auctionId,
        user_id: this.userId,
      });
    };


    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log("Message received from server:", message);

      // Handle specific server messages
      if (message.connectionId) {
        // Store the connection ID from the server
        this.connectionId = message.connectionId;
        console.log(`Connection ID set: ${this.connectionId}`);
      }

      if (message.remaining_time) {
        const remainingTime = message.remaining_time;
        // Update UI
        remainingTimeElement.textContent = remainingTime;
        if(remainingTime != "Auction has ended"){
          // Parse the remaining time into seconds for countdown logic
          const timeParts = remainingTime.split(":");
          const hours = parseInt(timeParts[0], 10);
          const minutes = parseInt(timeParts[1], 10);
          const seconds = parseInt(timeParts[2], 10);
          let totalSeconds = hours * 3600 + minutes * 60 + seconds;

          // Start countdown
          startCountdown(totalSeconds);
        }
      }

      
      if(message.auction_status == "in_progress"){
        if (bidButtonsDiv.style.display === 'none' || bidButtonsDiv.style.display === '') {
          bidButtonsDiv.style.display = 'block';
        }
      } else if (message.auction_status == "about_to_start" || message.auction_status == "ended") {
        bidButtonsDiv.style.display = 'none';
      }

      if (message.type === "leaderboardUpdate") {
        this.updateLeaderboard(message.leaderboard);
      } else if (message.type === "error") {
        console.error("Server error:", message.error);
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    this.socket.onclose = () => {
      console.log("WebSocket connection closed.");
    };
  }

  sendMessage(action, data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = { action, ...data };
      this.socket.send(JSON.stringify(message));
      console.log(`Message sent:`, message);
    } else {
      console.error("WebSocket is not open. Cannot send message.");
    }
  }

  updateLeaderboard(leaderboard) {
    const tableBody = document.querySelector(".leaderboard-table tbody");
    tableBody.innerHTML = ""; // Clear current leaderboard

    console.log("Leaderboard updated:", leaderboard);
    document.querySelector(".bid-frame span:last-child").textContent = `$${leaderboard[0]['bid_amount']}`;

    if (leaderboard.length === 0) {
      const row = document.createElement("tr");
      row.classList.add("no-bids-row");
      row.innerHTML = `
        <td colspan="4" class="no-bids-message">
          <div class="cell-content">No bids placed yet</div>
        </td>
      `;
      tableBody.appendChild(row);
      return;
    }

    leaderboard.forEach((entry, index) => {
      const row = document.createElement("tr");
      row.classList.add("table-row");

      row.innerHTML = `
        <td class="table-cell"><div class="cell-content">${index + 1}</div></td>
        <td class="table-cell"><div class="cell-content">${entry.user_name}</div></td>
        <td class="table-cell"><div class="cell-content">$${entry.bid_amount}</div></td>
        <td class="table-cell"><div class="cell-content">${new Date(
          entry.timestamp * 1000
        ).toLocaleTimeString()}</div></td>
      `;
      tableBody.appendChild(row);
    });

    this.topBid = leaderboard[0].bid_amount;
  }

  disconnectAndSendMessage() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      if (this.connectionId) {
        // Send the disconnect message with the connection ID
        this.sendMessage("disconnect", {
          connection_id: this.connectionId,
        });
      } else {
        console.error("Connection ID is not available. Cannot send disconnect message.");
      }
    }

    this.disconnect();
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      console.log("WebSocket disconnected.");
    }
  }
}

// Countdown logic to update time every second
function startCountdown(totalSeconds) {
  const interval = setInterval(() => {
      if (totalSeconds <= 0) {
          clearInterval(interval);
          remainingTimeElement.textContent = "Time is up!";
          return;
      }

      totalSeconds--;

      // Calculate hours, minutes, and seconds
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;

      // Update UI
      remainingTimeElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }, 1000);
}