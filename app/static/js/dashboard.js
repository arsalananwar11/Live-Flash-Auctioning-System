document.addEventListener('DOMContentLoaded', function () {
    const tabs = document.querySelectorAll('.tabs-group .tab-default, .tabs-group .tab-selected');
    const auctionRow = document.getElementById('auction-row');

    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            
            tabs.forEach(t => {
                t.classList.remove('tab-selected');
                t.classList.add('tab-default');
                const content = t.querySelector('.tab-content') || t.querySelector('.tab-default-content');
                if (content) {
                    content.classList.remove('tab-content');
                    content.classList.add('tab-default-content');
                }
            });

            this.classList.remove('tab-default');
            this.classList.add('tab-selected');
            const content = this.querySelector('.tab-default-content');
            if (content) {
                content.classList.remove('tab-default-content');
                content.classList.add('tab-content');
            }

            // Load corresponding content (Mock fetching auction data)
            const tabTitle = this.querySelector('.tab-title').innerText;
            console.log(`Loading data for ${tabTitle}`);

            // Fetch auction data from the server via an API request
            loadAuctionData(tabTitle);
        });
    });

    
});
