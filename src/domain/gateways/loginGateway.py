import requests
import logging
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
if os.getenv("RENDER") is None:
    load_dotenv()

def load_cached_token(context):
    """Load the cached token from a file if it exists and is still valid."""
    if os.path.exists(context["TOKEN_CACHE_FILE"]):
        with open(context["TOKEN_CACHE_FILE"], "r") as f:
            try:
                data = json.load(f)
                user_data = data.get(context["API_KEY"])
                if user_data:
                    token = user_data.get("token")
                    expiration = user_data.get("expiration")

                    if token and expiration:
                        exp_datetime = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
                        now_utc = datetime.now(timezone.utc)

                        if now_utc < exp_datetime:
                            logging.info("🔄 Using cached token.")
                            return token  # Token is still valid

                        logging.info("⚠️ Cached token expired. Fetching new one...")
            except json.JSONDecodeError:
                logging.info("⚠️ Token cache file is corrupted. Fetching new token...")

    return None  # No valid token found

def save_token(token, expiration, context):
    """Save the token and its expiration timestamp to a local file."""
    data = {}
    if os.path.exists(context["TOKEN_CACHE_FILE"]):
        with open(context["TOKEN_CACHE_FILE"], "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logging.info("⚠️ Token cache file is corrupted. Overwriting with new data...")

    data[context["API_KEY"]] = {"token": token, "expiration": expiration}

    with open(context["TOKEN_CACHE_FILE"], "w") as f:
        json.dump(data, f)

def login_via_context(context):
    """Fetch an authentication token, storing it if valid."""
    cached_token = load_cached_token(context)
    if cached_token:
        return cached_token

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": context["COMPANY_ID"],
        "x-customerid": context["CUSTOMER_ID"]
    }

    payload = {
        "UserLogin": context["USERNAME"],
        "Pswd": context["PASSWORD"]
    }

    logging.info(f"🔍 Logging in via: {context['LOGIN_URL']}")

    response = requests.post(context["LOGIN_URL"], headers=headers, json=payload, verify=False)

    logging.info(f"🔍 Response Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data is None:
                logging.info("❌ Login failed: Response data is None.")
                return None
                
            # Safely access nested data
            data_section = data.get("data")
            if data_section is None:
                logging.info("❌ Login failed: No 'data' section in response.")
                return None
                
            token = data_section.get("token")
            expiration = data_section.get("tokenExpiration")

            if token and expiration:
                logging.info("✅ Login successful! Token retrieved.")
                save_token(token, expiration, context)
                return token
            else:
                logging.info("❌ Login failed: Token or expiration not found in response.")
                return None
        except json.JSONDecodeError:
            logging.info("❌ Error: Response is not valid JSON.")
            return None
    else:
        logging.info(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def login_via_credentials(username, password):
    """
    Authenticate the user and return the full login response.
    """
    url = "https://www.ourclublogin.com/api/CustomerAuth/CustomerLogin"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": os.getenv("COMPANY_ID"),  # Use environment variable for COMPANY_ID
        "x-customerid": os.getenv("CUSTOMER_ID")  # Use environment variable for CUSTOMER_ID
    }

    payload = {
        "UserLogin": username,
        "Pswd": password
    }

    logging.info(f"🔍 Logging in via: {url}")

    # Make the POST request
    response = requests.post(url, headers=headers, json=payload)

    logging.info(f"🔍 Response Status Code: {response.status_code}")

    if response.status_code == 200:
        try:
            return response.json()  # Return the full response
        except json.JSONDecodeError:
            logging.info("❌ Error: Response is not valid JSON.")
            return None
    else:
        logging.info(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

# Main script execution
if __name__ == "__main__":
    # Example context for testing
    context = {
        "LOGIN_URL": "https://example.com/login",
        "COMPANY_ID": "12345",
        "CUSTOMER_ID": "67890",
        "USERNAME": "user",
        "PASSWORD": "pass",
        "API_KEY": "example_api_key",
        "TOKEN_CACHE_FILE": "token_cache.json"
    }
    auth_token = login_via_context(context)

    if auth_token:
        # Get today's date in YYYY-MM-DD format
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")