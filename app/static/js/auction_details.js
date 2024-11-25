const leaderboard = [
    {
        rank: 1,
        username: "JohnDoe",
        bid: "$1,200",
        time: "00:32:10"
    },
    {
        rank: 2,
        username: "JaneDoe",
        bid: "$1,100",
        time: "00:29:54"
    },
    {
        rank: 3,
        username: "BobSmith",
        bid: "$1,000",
        time: "00:27:32"
    },
    {
        rank: 4,
        username: "AliceJohnson",
        bid: "$900",
        time: "00:25:10"
    },
    {
        rank: 5,
        username: "MikeDavis",
        bid: "$800",
        time: "00:22:49"
    }
];

document.addEventListener("DOMContentLoaded", function() {
    const leaderboardTable = document.querySelector(".leaderboard-table tbody");
    leaderboardTable.innerHTML = ""; // Clear existing leaderboard

    leaderboard.forEach(leader => {
        const row = document.createElement("tr");
        row.classList.add("table-row");

        const rankCell = document.createElement("td");
        rankCell.classList.add("table-cell");
        rankCell.innerHTML = `<div class="cell-content">${leader.rank}</div>`;
        row.appendChild(rankCell);

        const usernameCell = document.createElement("td");
        usernameCell.classList.add("table-cell");
        usernameCell.innerHTML = `<div class="cell-content">${leader.username}</div>`;
        row.appendChild(usernameCell);

        const bidCell = document.createElement("td");
        bidCell.classList.add("table-cell");
        bidCell.innerHTML = `<div class="cell-content">${leader.bid}</div>`;
        row.appendChild(bidCell);

        const timeCell = document.createElement("td");
        timeCell.classList.add("table-cell");
        timeCell.innerHTML = `<div class="cell-content">${leader.time}</div>`;
        row.appendChild(timeCell);

        leaderboardTable.appendChild(row);
    });
});

document.addEventListener("DOMContentLoaded", function() {
    const increments = [5, 10, 15, 20];

    const bidButtonsDiv = document.querySelector(".bid-buttons");

    increments.forEach(increment => {
        const button = document.createElement("button");
        button.classList.add("bid-button");
        button.innerHTML = `<img src="https://cdn.builder.io/api/v1/image/assets/TEMP/6fa4a0e59d224dfd7dd2e280dd0a456208eb66c446f409fff1c6669a45432da6?placeholderIfAbsent=true&apiKey=ef34feccb14a4349a0b21d81082028c5" alt="" class="button-icon" /><span>${increment}%</span>`;
        button.addEventListener("click", function() {
            const currentBid = document.querySelector(".bid-frame span:last-child").textContent;
            const newBid = (Number(currentBid.replace(/[^\d.-]/g, "")) * (1 + increment / 100)).toFixed(2);
            document.querySelector(".bid-frame span:last-child").textContent = `$${newBid}`;
        });
        bidButtonsDiv.appendChild(button);
    });

    const customBidButton = document.createElement("button");
    customBidButton.classList.add("bid-button");
    customBidButton.innerHTML = `<img src="https://cdn.builder.io/api/v1/image/assets/TEMP/b3839e35b1bccdc5aaeccb24adf1904e8555b71edb26def35edde63ef1057946?placeholderIfAbsent=true&apiKey=ef34feccb14a4349a0b21d81082028c5" alt="" class="button-icon" /><span>Custom</span>`;
    bidButtonsDiv.appendChild(customBidButton);

    const customBidForm = document.createElement("form");
    customBidForm.classList.add("custom-input");
    customBidForm.innerHTML = `
        <label for="customAmount" class="visually-hidden">Custom Amount</label>
        <div class="input-content" aria-label="Custom Amount">
            <span class="dollar-sign">$</span>
            <input type="number" id="customAmount" placeholder="Custom Amount" style="border: none;" />
        </div>
    `;
    bidButtonsDiv.appendChild(customBidForm);
});