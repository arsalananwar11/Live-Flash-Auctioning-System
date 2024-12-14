import json
import os
import boto3
from botocore.exceptions import ClientError

ses = boto3.client("ses")

SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL")


def send_new_auction_email(recipients, auction_details):
    try:
        auction_item = auction_details.get("auction_item")
        auction_desc = auction_details.get("auction_desc")
        base_price = auction_details.get("base_price")
        start_time = auction_details.get("start_time")
        end_time = auction_details.get("end_time")
        created_by = auction_details.get("created_by")

        for recipient in recipients:
            email = recipient.get("email")
            user_name = recipient.get("user_name", "Participant")
            if not email:
                print(f"Skipping recipient without email: {recipient}")
                continue

            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #f4f4f4; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 20px;
                                        border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <h2 style="color: #333;">Hi {user_name},</h2>
                        <p style="color: #555;">We are excited to announce a new auction!</p>
                        <p style="color: #555;">Here are the details of the newly created auction:</p>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background-color: #fdfdfd;">
                            <tr><th style="text-align: left; padding: 10px;">Auction Item:</th><td style="padding: 10px;">{auction_item}</td></tr>
                            <tr><th style="text-align: left; padding: 10px;">Description:</th><td style="padding: 10px;">{auction_desc}</td></tr>
                            <tr><th style="text-align: left; padding: 10px;">Base Price:</th><td style="padding: 10px;">${base_price}</td></tr>
                            <tr><th style="text-align: left; padding: 10px;">Start Time:</th><td style="padding: 10px;">{start_time}</td></tr>
                            <tr><th style="text-align: left; padding: 10px;">End Time:</th><td style="padding: 10px;">{end_time}</td></tr>
                            <tr><th style="text-align: left; padding: 10px;">Created By:</th><td style="padding: 10px;">{created_by}</td></tr>
                        </table>
                        <p style="color: #555;">Get ready to place your bids and enjoy the excitement of the auction!</p>
                        <div style="text-align: center; margin-top: 20px;">
                            <a href="https://flash-bids.com/auctions/{auction_details.get("auction_id")}" style="background-color: #007bff; color: white;
                                                text-decoration: none; padding: 10px 20px; border-radius: 5px; display: inline-block;">View Auction</a>
                        </div>
                        <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 20px;">&copy; 2024 Auction Platform, All rights reserved.</p>
                    </div>
                </body>
            </html>
            """

            ses.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": f"New Auction Created: {auction_item}"},
                    "Body": {"Html": {"Data": body_html}},
                },
            )
            print(f"New auction notification email sent to {email}")

    except ClientError as e:
        print(f"Error sending email: {str(e)}")


def lambda_handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        email = message["email"]
        user_name = message["user_name"]
        auction_details = message["auction_details"]

        # Call the existing `send_new_auction_email` logic
        send_new_auction_email(
            [{"email": email, "user_name": user_name}], auction_details
        )
    return {"statusCode": 200, "body": "Emails sent successfully"}
