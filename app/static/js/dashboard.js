$(document).ready(function () {

    $('.tabs-group .tab-default, .tabs-group .tab-selected').on('click', function () {
        // Remove selected state from all tabs
        $('.tabs-group .tab-default, .tabs-group .tab-selected').each(function () {
            $(this).removeClass('tab-selected').addClass('tab-default');
            $(this).find('.tab-content').removeClass('tab-content').addClass('tab-default-content');
        });

        // Add selected state to the clicked tab
        $(this).removeClass('tab-default').addClass('tab-selected');
        $(this).find('.tab-default-content').removeClass('tab-default-content').addClass('tab-content');

        // Load corresponding content
        const tabTitle = $(this).find('.tab-title').text();
        loadAuctionData(tabTitle);
    });
});

function loadAuctionData(tabTitle) {
            $.getJSON('/static/dummyData/sampleData.json', function (data) {
                const auctionData = data[tabTitle];
                const auctionRow = $('.auction-row');
                auctionRow.empty(); // Clear existing cards

                $.each(auctionData, function (index, auction) {
                    // Create auction card HTML
                    const auctionCard = `
                        <article class="auction-column">
                            <div class="auction-card">
                                <div class="card-content">
                                    <header class="card-header">
                                        <div class="avatar">
                                            <div class="avatar-background">${auction.organizer.charAt(0)}</div>
                                        </div>
                                        <div class="header-text">
                                            <h2 class="header-title">${auction.product_name}</h2>
                                            <p class="header-subtitle">${auction.type}</p>
                                        </div>
                                    </header>
                                    <div class="card-media">
                                        <img src="https://cdn.builder.io/api/v1/image/assets/TEMP/d76c5f972065984933a0e35e9320b1baa3941e5b04710def9bb3b23c60478105?placeholderIfAbsent=true&apiKey=81324c3163b0409590024e6a0b27b016" alt="Product image" class="card-image">
                                    </div>
                                    <div class="card-details">
                                        <div class="card-headline">
                                            <p class="card-subtitle">Start/End Time: ${auction.start_end_time}</p>
                                        </div>
                                        <p class="card-description">${auction.description}</p>
                                        <div class="card-actions">
                                            <button class="primary-action">
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
            }).fail(function (jqXHR, textStatus, errorThrown) {
                console.error('There has been a problem with your fetch operation:', errorThrown);
            });
        }


// Load "All Auction" data by default on page load
loadAuctionData("All Auction");