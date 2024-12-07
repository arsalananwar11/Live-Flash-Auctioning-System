document.addEventListener("DOMContentLoaded", function () {
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
        const currentBid = document.querySelector(".bid-frame span:last-child").textContent;
        const newBid = (
          Number(currentBid.replace(/[^\d.-]/g, "")) * (1 + increment / 100)
        ).toFixed(2);
        document.querySelector(".bid-frame span:last-child").textContent = `$${newBid}`;
  
        // Send the new bid through WebSocket
        placeBid(newBid);
      });
      bidButtonsDiv.appendChild(button);
    });
  
    // Create custom bid button and form
    // const customBidButton = document.createElement("button");
    // customBidButton.classList.add("bid-button");
    // customBidButton.innerHTML = `<img src="https://cdn.builder.io/api/v1/image/assets/TEMP/b3839e35b1bccdc5aaeccb24adf1904e8555b71edb26def35edde63ef1057946?placeholderIfAbsent=true&apiKey=ef34feccb14a4349a0b21d81082028c5" alt="" class="button-icon" /><span>Custom</span>`;
    // bidButtonsDiv.appendChild(customBidButton);

    // const customBidForm = document.createElement("form");
    // customBidForm.classList.add("custom-input");
    // customBidForm.innerHTML = `
    //     <label for="customAmount" class="visually-hidden">Custom Amount</label>
    //     <div class="input-content" aria-label="Custom Amount">
    //         <span class="dollar-sign">$</span>
    //         <input type="number" id="customAmount" placeholder="Custom Amount" style="border: none;" />
    //     </div>
    // `;
    // bidButtonsDiv.appendChild(customBidForm);
  
    // Handle custom bid submission
    // customBidButton.addEventListener("click", function () {
    //   const customAmount = document.getElementById("customAmount").value;
    //   if (customAmount) {
    //     const newBid = parseFloat(customAmount).toFixed(2);
    //     document.querySelector(".bid-frame span:last-child").textContent = `$${newBid}`;
  
    //     // Send the custom bid through WebSocket
    //     placeBid(newBid);
    //   } else {
    //     console.error("Custom bid amount is empty.");
    //   }
    // });
  });
