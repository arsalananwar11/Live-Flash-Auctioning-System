let loggedInUserId = null; // Global variable to store the logged-in user ID

$(document).ready(async function () {
  try {
    // Fetch user details and set loggedInUserId
    const response = await fetch("/user-details");
    if (!response.ok) {
      throw new Error(`Failed to fetch user details: ${response.statusText}`);
    }

    const userDetails = await response.json();
    loggedInUserId = userDetails.id; // Assign user ID to the global variable
    console.log(`Logged-in User ID: ${loggedInUserId}`);
  } catch (error) {
    console.error("Error fetching user details:", error);
    alert("Failed to fetch user details. Please try again.");
  }
  // Function to connect to WebSocket
  async function connectToWebSocket(auctionID) {
    if (!loggedInUserId) {
      console.error(
        "User ID is not available. Unable to connect to WebSocket."
      );
      return false; // Connection failed
    }

    try {
      // Fetch the WebSocket URL
      const response = await fetch("/get-websocket-url");
      if (!response.ok) {
        throw new Error(
          `Failed to fetch WebSocket URL: ${response.statusText}`
        );
      }

      const data = await response.json();
      const websocketUrl = data.websocket_url;

      return new Promise((resolve, reject) => {
        try {
          const socket = new WebSocket(
            `${websocketUrl}?auction_id=${auctionID}&user_id=${loggedInUserId}`
          );

          socket.onopen = function () {
            console.log("WebSocket connection established.");
            const message = {
              action: "create",
              auction_id: auctionID,
              user_id: loggedInUserId,
            };
            try {
              socket.send(JSON.stringify(message));
              console.log(
                `Sent connection ID request for auction: ${auctionID}`
              );
              resolve(true); // WebSocket connection successful
            } catch (sendError) {
              console.error("Error sending WebSocket message:", sendError);
              reject(sendError);
            }
          };

          socket.onmessage = function (event) {
            try {
              console.log("Message received from server:", event.data);
              const message = JSON.parse(event.data);
              if (message.connectionId) {
                console.log(`Connection ID: ${message.connectionId}`);
              }
            } catch (messageError) {
              console.error(
                "Error processing WebSocket message:",
                messageError
              );
            }
          };

          socket.onerror = function (error) {
            console.error("WebSocket error occurred:", error);
            reject(error); // Connection failed
          };

          socket.onclose = function (event) {
            console.log(
              `WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`
            );
          };
        } catch (connectionError) {
          console.error(
            "Error establishing WebSocket connection:",
            connectionError
          );
          reject(connectionError);
        }
      });
    } catch (fetchError) {
      console.error("Error fetching WebSocket URL:", fetchError);
      return false; // Connection failed
    }
  }

  // Handle form submission
  $("#auction-form").submit(async function (event) {
    event.preventDefault();

    $(".create-button").prop("disabled", true).text("Processing...");

    const formData = new FormData(this);

    const images = document.getElementById("image-upload").files;
    if (images.length > 0) {
      const promises = Array.from(images).map((image) => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(",")[1]);
          reader.onerror = (e) => reject(e);
          reader.readAsDataURL(image);
        });
      });

      try {
        const base64Images = await Promise.all(promises);
        formData.append("images", JSON.stringify(base64Images));

        // Submit the auction creation request
        const response = await $.ajax({
          url: this.action,
          type: this.method,
          data: formData,
          contentType: false,
          processData: false,
        });

        console.log("Auction created successfully!");
        console.log("Server response:", response);

        let data;
        try {
          data = typeof response === "string" ? JSON.parse(response) : response;
        } catch (parseError) {
          console.error("Error parsing server response:", parseError);
          alert("Failed to process server response. Please try again.");
          $(".create-button").prop("disabled", false).text("Try Again");
          return;
        }

        // Extract auction_id from the response
        console.log("Data: ", data);
        const auctionId = data.data?.auction_id || null;

        if (auctionId) {
          console.log(`Auction ID: ${auctionId}`);

          // Try to connect to WebSocket
          const isWebSocketConnected = await connectToWebSocket(auctionId);

          if (isWebSocketConnected) {
            console.log("WebSocket connected. Redirecting to dashboard...");
            window.location.href = `/dashboard`;
          } else {
            throw new Error("Failed to establish WebSocket connection.");
          }
        } else {
          console.error(
            "Auction ID is missing in the server response:",
            response
          );
          alert(
            "Auction created successfully, but no auction ID was returned. Please contact support."
          );
          $(".create-button").prop("disabled", false).text("Try Again");
        }
      } catch (error) {
        // Log and alert the error
        console.error(
          "Error during auction creation or WebSocket connection:",
          error
        );
        alert(
          "Failed to create auction or connect to WebSocket. Please try again."
        );
        $(".create-button").prop("disabled", false).text("Try Again");
      }
    } else {
      alert("Please upload at least one image.");
      $(".create-button").prop("disabled", false).text("Create Auction");
    }
  });

  // Handle image selection
  $("#image-upload").change(function () {
    const files = this.files;
    const previewContainer = $("#image-preview");
    previewContainer.empty();

    if (files.length > 0) {
      $(".upload-text").text(`${files.length} image(s) selected`);

      Array.from(files).forEach((file) => {
        const reader = new FileReader();
        reader.onload = (event) => {
          const img = $("<img>").attr("src", event.target.result);
          previewContainer.append(img);
        };
        reader.readAsDataURL(file);
      });
    } else {
      $(".upload-text").text("Click to Upload Images");
      previewContainer.empty();
    }
  });
});
