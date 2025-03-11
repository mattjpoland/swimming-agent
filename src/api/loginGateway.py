import requests
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.constants import TOKEN_CACHE_FILE, COMPANY_ID, CUSTOMER_ID, USERNAME, PASSWORD, LOGIN_URL


# Load environment variables
if os.getenv("RENDER") is None:
    load_dotenv()

def load_cached_token():
    """Load the cached token from a file if it exists and is still valid."""
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
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


def save_token(token, expiration):
    """Save the token and its expiration timestamp to a local file."""
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump({"token": token, "expiration": expiration}, f)


def login():
    """Fetch an authentication token, storing it if valid."""
    cached_token = load_cached_token()
    if cached_token:
        return cached_token

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": COMPANY_ID,
        "x-customerid": CUSTOMER_ID
    }

    payload = {
        "UserLogin": USERNAME,
        "Pswd": PASSWORD
    }

    print(f"🔍 Logging in via: {LOGIN_URL}")

    response = requests.post(LOGIN_URL, headers=headers, json=payload, verify=False)

    print(f"🔍 Response Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            token = data.get("data", {}).get("token")
            expiration = data.get("data", {}).get("tokenExpiration")  # Assuming response contains an expiration field

            if token and expiration:
                print("✅ Login successful! Token retrieved.")
                save_token(token, expiration)
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

        return None



# Main script execution
if __name__ == "__main__":
    auth_token = login()

    if auth_token:
        # Get today's date in YYYY-MM-DD format
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")


