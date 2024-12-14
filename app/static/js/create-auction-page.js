$(document).ready(function () {
    // Handle form submission
    $("#auction-form").submit(function (event) {
        event.preventDefault();
        
        $(".create-button").prop("disabled", true).text("Processing...");

        const formData = new FormData(this);
        
        const startDate = $("#start-date").val(); 
        const startTime = $("#start-time").val(); 
        const endDate = $("#end-date").val();     
        const endTime = $("#end-time").val();     
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        if (startDate && startTime && endDate && endTime) {
            const startDateTime = new Date(`${startDate}T${startTime}`);
            const endDateTime = new Date(`${endDate}T${endTime}`);
            
            const startDateTimeUTC = startDateTime.toISOString();
            const endDateTimeUTC = endDateTime.toISOString();

            formData.append("start_time_utc", startDateTimeUTC);
            formData.append("end_time_utc", endDateTimeUTC);
            formData.append("timezone", timezone);
        } else {
            alert("Please fill in the start and end date/time fields.");
            $(".create-button").prop("disabled", false).text("Create Auction");
            return;
        }
        

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

            Promise.all(promises)
                .then((base64Images) => {
                    formData.append("images", JSON.stringify(base64Images));
                    $.ajax({
                        url: this.action, 
                        type: this.method, 
                        data: formData,
                        contentType: false,
                        processData: false,
                        success: function () {
                            alert("Auction created successfully!");
                            window.location.href = "/dashboard";
                        },
                        error: function (xhr) {
                            console.error("Error:", xhr.responseText);
                            alert("Failed to create auction.");
                            $(".create-button").prop("disabled", false).text("Try Again");
                        },
                    });
                })
                .catch((err) => {
                    alert("Error processing images.");
                    console.error(err);
                });
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
