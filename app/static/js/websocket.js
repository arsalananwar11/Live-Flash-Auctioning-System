export class AuctionWebSocket {
    constructor(websocketUrl, auctionId, userId) {
      this.websocketUrl = websocketUrl;
      this.auctionId = auctionId;
      this.userId = userId;
      this.socket = null;
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
  
      leaderboard.forEach((entry, index) => {
        const row = document.createElement("tr");
        row.classList.add("table-row");
  
        row.innerHTML = `
          <td class="table-cell"><div class="cell-content">${index + 1}</div></td>
          <td class="table-cell"><div class="cell-content">${entry.username}</div></td>
          <td class="table-cell"><div class="cell-content">$${entry.bid_amount}</div></td>
          <td class="table-cell"><div class="cell-content">${new Date(
            entry.timestamp * 1000
          ).toLocaleTimeString()}</div></td>
        `;
        tableBody.appendChild(row);
      });
    }
  
    disconnect() {
      if (this.socket) {
        this.socket.close();
        console.log("WebSocket disconnected.");
      }
    }
  }