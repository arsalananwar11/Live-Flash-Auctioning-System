# Live-Flash-Auctioning-System

The Live Flash Auctioning System is an innovative platform that facilitates real-time auctions with minimal latency. Auctioneers can host live video auctions, engaging participants globally. The platform ensures fair bidding practices through synchronized countdown timers and instant notifications, allowing users to participate from any location seamlessly.

## Product Features:
1. #### Real-Time Bidding Interface:
  - Auctioneers can input product details, including auction date, time, and duration.
  - Users can view products at the specified times, see the number of bids placed, and participate in real-time bidding.
2. #### Bidding Mechanism:
  - Participants can place bids in real-time using WebSockets for low-latency communication.
  - The system efficiently handles concurrent bids, ensuring accuracy and fairness.
  - The highest bidder at the end of the auction wins the item.
3. #### Dynamic Countdown Timer:
  - A synchronized countdown timer is displayed to all users, ensuring fairness.
  - Utilizes AWS Time Sync Service for accurate timekeeping across all users.
4. #### Auction Notifications:
  - Integration with Amazon Simple Notification Service (SNS) to send personalized notifications to users about upcoming auctions.
  - Notifications include product details and auction timings based on user interests collected during sign-up.
5. #### Sniping Prevention:
  - If a bid is placed within the last 30 seconds, the auction timer extends automatically by a set duration (e.g., 1 minute).
  - Extensions are communicated instantly to all participants, preventing last-second bidding advantages.
6. #### Scalability:
  - Employs AWS EC2 with auto-scaling groups to adjust resources dynamically based on user traffic.
  - Ensures consistent performance during peak times and cost-efficiency during low traffic periods.
7. #### Data Storage and Analysis:
  - All bids, auction details, and timer extensions are stored in Amazon DynamoDB for record-keeping and analysis.
  - Enables detailed analytics on bidding behavior and auction performance.
8. #### User Authentication:
  - Secure user authentication and management using AWS Cognito.
  - Supports user profile management and interest tracking for personalized experiences.
9. #### Media Storage:
  - Product images and videos are stored in Amazon S3, ensuring fast and reliable media access.
10. #### Real-Time Data Synchronization:
  - Uses AWS AppSync or Amazon Kinesis for real-time data synchronization between the server and clients.
  - Ensures all users receive instantaneous updates on bids and timer changes.

## Tech Stack
- WebSockets for low-latency real-time communication
- Amazon DynamoDB to store bids, auction product details, and event history 
- Amazon S3 to store any associated media (e.g., pictures/video)
- AWS AppSync or Amazon Kinesis for real-time data sync
- AWS Time Sync for Network Time Protocol
- Amazon SNS for notifications to inform users about upcoming auctions
- Amazon SQS to accept bids from users
- AWS Cognito for user authentication
- EC2 with Autoscaling groups to manage resources based on fluctuating user traffic

## Data Sources:
- User Sourced Data:
  - User Data: Collected during sign-up via AWS Cognito, including interests and optional location data. Used for personalized notifications and targeted advertisements.
  - Auction Data: Product details, auction schedules, and historical data stored in Amazon DynamoDB. Includes information on bids placed, timestamps, and auction outcomes.
  - Bidding Data: Real-time bid submissions handled through Amazon SQS for efficient processing. Stored for analysis and to ensure transparency in the bidding process.
  - Media Content: Product images and videos uploaded by auctioneers to Amazon S3. Ensures high availability and scalability for media assets.

## Existing Products:
1. eBay Live Auctions:
  - Offers live auction experiences but may lack synchronized countdown timers and advanced sniping prevention features.
  - Latency issues can affect the real-time bidding experience.
2. Invaluable:
  - Provides live auctions with real-time bidding capabilities.
  - Does not emphasize dynamic auction extensions to prevent sniping.
3. LiveAuctioneers:
  - Hosts live auctions for a global audience.
  - May face challenges with latency and does not fully address peak traffic scalability.
