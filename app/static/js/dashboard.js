let loggedInUserId = null; // Global variable to store the logged-in user ID

    // Utility function to transform tab titles to mode strings
    function transformTabTitle(tabTitle) {
      return tabTitle.toLowerCase().replace(/\s+/g, '_');
  }
  
  function escapeHtml(text) {
      return $('<div>').text(text).html();
  }

$(document).ready(function () {
    $('.tabs-group .tab-default, .tabs-group .tab-selected').on('click', function () {
        // Remove selected state from all tabs
        $('.tabs-group .tab-default, .tabs-group .tab-selected').each(function () {
            $(this).removeClass('tab-selected').addClass('tab-default');
            $(this).find('.tab-content').removeClass('tab-content').addClass('tab-default-content');
        });
  // Fetch user details on page load
  fetch("/user-details", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("token")}`, // Add if using token validation
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("User Details:", data);
      if (data && data.id) {
        loggedInUserId = data.id; // Store the user ID globally
        console.log(`Logged-in User ID: ${loggedInUserId}`);
      }
      // You can use user details to customize the dashboard UI, like showing the username
      if (data && data.name) {
        $(".user-name").text(data.name); // Assuming there's an element to show the user's name
      }
    })
    .catch((error) => {
      console.error("Failed to fetch user details:", error);
    });

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

        // Get the tab title, transform it, and load corresponding content
        const rawTabTitle = $(this).find('.tab-title').text();
        const mode = transformTabTitle(rawTabTitle);
        loadAuctionData(mode);
    });
});

});

function renderAuctionData(auctions) {
  const auctionRow = $('.auction-row');
  auctionRow.empty(); // Clear existing cards

  if (!Array.isArray(auctions) || auctions.length === 0) {
      auctionRow.html('<p>No auctions available.</p>');
      return;
  }

  $.each(auctions, function (_, auction) {
      // Validate required fields with updated field names
      console.log('Auction:', auction);
      if (!auction.auction_item || !auction.start_time || !auction.auction_desc) {
          console.warn('Incomplete auction data:', auction);
          return; // Skip this auction
      }

      // Safely access images
      const imageUrl = auction.images && auction.images.length > 0 && auction.images[0].base64
          ? `data:image/jpeg;base64,${auction.images[0].base64}`
          : 'https://via.placeholder.com/150'; // Fallback image

      // Create auction card HTML with updated field names
      auctionRow.append(`
          <article class="auction-column">
          <div class="auction-card">
              <div class="card-content">
              <header class="card-header">
                  <div class="header-text">
                  <h2 class="header-title">${escapeHtml(auction.auction_item)}</h2>
                  </div>
              </header>
              <div class="card-media">
                  <img src="${imageUrl}" alt="Product image" class="card-image">
              </div>
              <div class="card-details">
                  <div class="card-headline">
                  <p class="card-subtitle">Start Time: ${escapeHtml(auction.start_time)}</p>
                  <p class="card-subtitle">End Time: ${escapeHtml(auction.end_time)}</p>
                  </div>
                  <p class="card-description">${escapeHtml(auction.auction_desc)}</p>
                  <div class="card-actions">
                  <button class="primary-action join-button" data-auction-id="${auction.auction_id}">
                      <span class="action-state">Join</span>
                  </button>
                  </div>
              </div>
              </div>
          </div>
          </article>
      `);
  });
}

function loadAuctionData(tabTitle) {
  const auctionRow = $('.auction-row');
  auctionRow.empty().html('<p>Loading auctions...</p>');

  // Determine the mode based on tabTitle
  let mode = 'all_auction';
  let requestType = 'GET';
  let requestData = null;
  if (tabTitle === 'my_auctions') {
      mode = 'my_auctions';
  } else if (tabTitle === 'upcoming_auctions') {
      mode = 'upcoming_auctions';
  } else {
      mode = 'all_auction';
  }

  // Prepare AJAX settings
  let ajaxSettings = {
      url: '/api/get-auctions',
      type: requestType,
      dataType: 'json',
      success: function (data) {
          // console.log('Auction data loaded:', data);
      
          renderAuctionData(data);
      },
      error: function (jqXHR, textStatus, errorThrown) {
          console.error('There has been a problem with your fetch operation:', errorThrown);
          auctionRow.html('<p>Failed to load auctions. Please try again later.</p>');
      }
  };

  if (requestType === 'POST') {
      ajaxSettings.contentType = 'application/json';
      ajaxSettings.data = requestData;
  } else if (requestType === 'GET') {
      ajaxSettings.url += `?mode=${encodeURIComponent(mode)}`;
  }

  // Make the AJAX request
  $.ajax(ajaxSettings);
}

function connectToWebSocket(auctionID) {

  if (!loggedInUserId) {
    console.error("User ID is not available. Unable to connect to WebSocket.");
    return;
  }

  // Fetch the WebSocket URL from the backend
  fetch("/get-websocket-url")
    .then((response) => response.json())
    .then((data) => {
      const websocketUrl = data.websocket_url;
      
      // Establish WebSocket connection with auction_id as query parameter
      const socket = new WebSocket(
        `${websocketUrl}?auction_id=${auctionID}&user_id=${loggedInUserId}`
      );

      // WebSocket event handlers
      socket.onopen = function () {
        console.log("WebSocket connection established.");
        alert(`You have joined the auction: ${auctionID}`);
        console.log(
          `Connected to auction: ${auctionID} as user: ${loggedInUserId}`
        );
        const message = { action: "getConnectionId" };
        socket.send(JSON.stringify(message));

        // Send a ping every 5 minutes
        setInterval(() => {
          console.log("Sending ping to keep the connection alive");
          socket.send(JSON.stringify({ action: "ping" }));
        }, 5 * 60 * 1000); // 5 minutes
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

$(document).on("click", ".join-button", function () {
    const auctionID = $(this).data("auction-id");
    connectToWebSocket(auctionID);
    console.log("Button Clicked");
    console.log(`Attempting to join auction: ${auctionID}`);
    const auctionId = $(this).data('auction-id');
    console.log('Join auction:', auctionId);
    window.location.href = `/auctions/${auctionId}`;
});
// Load "All Auction" data by default on page load


loadAuctionData("All Auction");
