$(document).ready(function () {
    // Handle form submission
    $("#create-auction-form").submit(function (event) {
        event.preventDefault(); // Prevent default form submission

        // Get form data
        const formData = new FormData(this);

        // Handle image upload and convert to Base64
        const images = document.getElementById("image-upload").files;
        if (images.length > 0) {
            const promises = Array.from(images).map((image) => {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result.split(",")[1]); // Extract Base64 string
                    reader.onerror = (e) => reject(`Error reading file: ${e.target.error.message}`);
                    reader.readAsDataURL(image);
                });
            });

            // Show processing state
            $(".create-button").prop("disabled", true).text("Processing...");

            // Convert images to Base64 and append to formData
            Promise.all(promises)
                .then((base64Images) => {
                    formData.append("images", JSON.stringify(base64Images));

                    // Send data to the Flask controller
                    $.ajax({
                        url: "/create-auction",
                        type: "POST",
                        data: formData,
                        contentType: false,
                        processData: false,
                        success: function (response) {
                            alert("Auction created successfully!");
                            window.location.href = "/dashboard"; // Redirect to dashboard
                        },
                        error: function (xhr, status, error) {
                            console.error("Error creating auction:", error);
                            alert("Failed to create the auction. Please try again.");
                        },
                        complete: function () {
                            $(".create-button").prop("disabled", false).text("Create Auction");
                        },
                    });
                })
                .catch((error) => {
                    console.error("Error processing images:", error);
                    alert("Error processing images. Please try again.");
                    $(".create-button").prop("disabled", false).text("Create Auction");
                });
        } else {
            alert("Please upload at least one image.");
        }
    });

    // Handle image selection
    $("#image-upload").change(function () {
        const files = this.files;
        if (files.length > 0) {
            $(".upload-text").text(`${files.length} image(s) selected`);
        } else {
            $(".upload-text").text("Click to Upload Images");
        }
    });
    // Handle image selection
    $("#image-upload").change(function () {
        const files = this.files;
        const previewContainer = $("#image-preview");
        previewContainer.empty(); // Clear existing images

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
