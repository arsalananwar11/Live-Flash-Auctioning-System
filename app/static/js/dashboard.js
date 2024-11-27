$(document).ready(function () {
  $(".tabs-group .tab-default, .tabs-group .tab-selected").on(
    "click",
    function () {
      // Remove selected state from all tabs
      $(".tabs-group .tab-default, .tabs-group .tab-selected").each(
        function () {
          $(this).removeClass("tab-selected").addClass("tab-default");
          $(this)
            .find(".tab-content")
            .removeClass("tab-content")
            .addClass("tab-default-content");
        }
      );

      // Add selected state to the clicked tab
      $(this).removeClass("tab-default").addClass("tab-selected");
      $(this)
        .find(".tab-default-content")
        .removeClass("tab-default-content")
        .addClass("tab-content");

      // Load corresponding content
      const tabTitle = $(this).find(".tab-title").text();
      loadAuctionData(tabTitle);
    }
  );
});

function connectToWebSocket(auctionID) {
  //Hardcoded user id
  const userID = "user123";
  // Fetch the WebSocket URL from the backend
  fetch("/get-websocket-url")
    .then((response) => response.json())
    .then((data) => {
      const websocketUrl = data.websocket_url;

      // Establish WebSocket connection with auction_id as query parameter
      const socket = new WebSocket(
        `${websocketUrl}?auction_id=${auctionID}&user_id=${userID}`
      );

      // WebSocket event handlers
      socket.onopen = function () {
        console.log("WebSocket connection established.");
        alert(`You have joined the auction: ${auctionID}`);
        const message = { action: "getConnectionId" };
        socket.send(JSON.stringify(message));
      };

      socket.onmessage = function (event) {
        console.log("Message received from server:", event.data);

        // Parse the received message
        const message = JSON.parse(event.data);

        // Check if the message contains a connection ID
        if (message.connectionId) {
          console.log(`Connection ID: ${message.connectionId}`);
        }
      };

      socket.onerror = function (error) {
        console.error("WebSocket error:", error);
      };

      socket.onclose = function () {
        console.log("WebSocket connection closed.");
      };
    })
    .catch((error) => {
      console.error("Error fetching WebSocket URL:", error);
    });
}

function loadAuctionData(tabTitle) {
  $.getJSON("/static/dummyData/sampleData.json", function (data) {
    const auctionData = data[tabTitle];
    const auctionRow = $(".auction-row");
    auctionRow.empty(); // Clear existing cards

    $.each(auctionData, function (index, auction) {
      // Create auction card HTML
      const auctionCard = `
                        <article class="auction-column">
                            <div class="auction-card">
                                <div class="card-content">
                                    <header class="card-header">
                                        <div class="avatar">
                                            <div class="avatar-background">${auction.organizer.charAt(
                                              0
                                            )}</div>
                                        </div>
                                        <div class="header-text">
                                            <h2 class="header-title">${
                                              auction.auction_item
                                            }</h2>
                                            <p class="header-subtitle">${
                                              auction.type
                                            }</p>
                                        </div>
                                    </header>
                                    <div class="card-media">
                                        <img src="https://cdn.builder.io/api/v1/image/assets/TEMP/d76c5f972065984933a0e35e9320b1baa3941e5b04710def9bb3b23c60478105?placeholderIfAbsent=true&apiKey=81324c3163b0409590024e6a0b27b016" alt="Product image" class="card-image">
                                    </div>
                                    <div class="card-details">
                                        <div class="card-headline">
                                            <p class="card-subtitle">Start/End Time: ${
                                              auction.start_end_time
                                            }</p>
                                        </div>
                                        <p class="card-description">${
                                          auction.description
                                        }</p>
                                        <div class="card-actions">
                                            <button class="primary-action join-button"
                                            data-auction-id="${
                                              auction.auction_id
                                            }">
                                                <span class="action-state">Join</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </article>
                    `;
      auctionRow.append(auctionCard);
    });

    $(".join-button").on("click", function () {
      //   const auctionId = $(this).data("auction-id");
      const auctionID = $(this).data("auction-id");
      connectToWebSocket(auctionID);
      console.log("Button Clicked");
      console.log(`Attempting to join auction: ${auctionID}`);
    });
  }).fail(function (jqXHR, textStatus, errorThrown) {
    console.error(
      "There has been a problem with your fetch operation:",
      errorThrown
    );
  });
}

// Load "All Auction" data by default on page load
loadAuctionData("All Auction");
