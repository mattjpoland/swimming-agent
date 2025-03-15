import requests
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
                token = data.get("token")
                expiration = data.get("expiration")

                if token and expiration:
                    exp_datetime = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
                    now_utc = datetime.now(timezone.utc)

                    if now_utc < exp_datetime:
                        print("🔄 Using cached token.")
                        return token  # Token is still valid

                    print("⚠️ Cached token expired. Fetching new one...")
            except json.JSONDecodeError:
                print("⚠️ Token cache file is corrupted. Fetching new token...")

    return None  # No valid token found

def save_token(token, expiration, context):
    """Save the token and its expiration timestamp to a local file."""
    with open(context["TOKEN_CACHE_FILE"], "w") as f:
        json.dump({"token": token, "expiration": expiration}, f)

def login(context):
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

    print(f"🔍 Logging in via: {context['LOGIN_URL']}")

    response = requests.post(context["LOGIN_URL"], headers=headers, json=payload, verify=False)

    print(f"🔍 Response Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            token = data.get("data", {}).get("token")
            expiration = data.get("data", {}).get("tokenExpiration")  # Assuming response contains an expiration field

            if token and expiration:
                print("✅ Login successful! Token retrieved.")
                save_token(token, expiration, context)
                return token
            else:
                print("❌ Login failed: Token or expiration not found in response.")
                return None
        except json.JSONDecodeError:
            print("❌ Error: Response is not valid JSON.")
            return None
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
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
        "TOKEN_CACHE_FILE": "token_cache.json"
    }
    auth_token = login(context)

    if auth_token:
        # Get today's date in YYYY-MM-DD format
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")


