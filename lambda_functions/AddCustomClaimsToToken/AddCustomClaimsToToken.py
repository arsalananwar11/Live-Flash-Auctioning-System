def lambda_handler(event, context):
    # Extract the user's attributes from the event object
    user_attributes = event["request"]["userAttributes"]

    # Example: Add custom claims
    custom_claims = {
        "name": user_attributes.get("name", ""),
        "role": user_attributes.get(
            "custom:role", "user"
        ),  # custom attribute (example: 'role')
    }

    # Add custom claims to the token
    event["response"]["claimsOverrideDetails"] = {
        "claimsToAddOrOverride": custom_claims
    }

    if user_attributes.get("email_verified") == "true":
        event["response"]["claimsOverrideDetails"]["isVerified"] = True
    else:
        event["response"]["claimsOverrideDetails"]["isVerified"] = False

    return event
