function convertUTCToLocalTimeTime(utcTime) {
  const localDate = new Date(new Date(`${utcTime}Z`).toLocaleString('en-US', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone }));
  return localDate.toLocaleString(); 
}

document.addEventListener("DOMContentLoaded", function () {

    const startTimeElement = document.getElementById("start-time");
    const endTimeElement = document.getElementById("end-time");

    if (startTimeElement) {
        const localStartTime = convertUTCToLocalTimeTime(startTimeElement.textContent.trim());
        startTimeElement.textContent = localStartTime;
    }

    if (endTimeElement) {
        const localEndTime = convertUTCToLocalTimeTime(endTimeElement.textContent.trim());
        endTimeElement.textContent = localEndTime;
    }

    const increments = [5, 10, 15, 20];
    const bidButtonsDiv = document.querySelector(".bid-buttons");
  
    function placeBid(newBid) {
      if (window.auctionSocket) {
        window.auctionSocket.sendMessage("placeBid", {
          auction_id: window.auctionSocket.auctionId,
          user_id: window.auctionSocket.userId,
          user_name: window.auctionSocket.userName,
          bid_amount: parseFloat(newBid),
        });
      } else {
        console.error("WebSocket connection is not available.");
      }
    }
  
    // Create bid increment buttons
    increments.forEach((increment) => {
      const button = document.createElement("button");
      button.classList.add("bid-button");

      button.innerHTML = `
        <img src="https://cdn.builder.io/api/v1/image/assets/TEMP/6fa4a0e59d224dfd7dd2e280dd0a456208eb66c446f409fff1c6669a45432da6?placeholderIfAbsent=true&apiKey=ef34feccb14a4349a0b21d81082028c5" alt="" class="button-icon" />
        <span>${increment}%</span>
      `;
      button.addEventListener("click", function () {
        const currentBid = document.getElementById("top-bid").textContent;
        const newBid = (
          Number(currentBid.replace(/[^\d.-]/g, "")) * (1 + increment / 100)
        ).toFixed(2);
        // document.querySelector(".bid-frame span:last-child").textContent = `$${newBid}`;
  
        // Send the new bid through WebSocket
        placeBid(newBid);
      });
      bidButtonsDiv.appendChild(button);
    });
  });
