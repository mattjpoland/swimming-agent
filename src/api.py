import os
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

TOKEN_CACHE_FILE = "token_cache.json"  # File to store token locally

# Load environment variables from .env file (only in local development)
if os.getenv("RENDER") is None:
    load_dotenv()

# Load configuration from environment variables
API_URL = os.getenv("API_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
COMPANY_ID = os.getenv("COMPANY_ID")
CUSTOMER_ID = os.getenv("CUSTOMER_ID")
AVAILABILITY_URL = os.getenv("AVAILABILITY_URL")


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

    print(f"🔍 API_URL: {API_URL}")

    response = requests.post(API_URL, headers=headers, json=payload, verify=False)

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


def check_swim_lane_availability(token, date_str, item_id):
    """Fetch swim lane availability using the cached or newly obtained token."""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": COMPANY_ID,
        "x-customerid": CUSTOMER_ID,
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "ClubId": 2,  # Michigan Athletic Club
        "PrimaryCustomerId": int(CUSTOMER_ID),
        "AdditionalCustomerIds": [],
        "ItemId": item_id,
        "JsonSelectedBook": "null",
        "StartDate": f"{date_str}T05:00:00.000Z",
        "EndDate": f"{date_str}T05:00:00.000Z"
    }

    response = requests.post(AVAILABILITY_URL, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        print(f"✅ Successfully retrieved availability for ItemId {item_id}!")
        return response.json()
    else:
        print(f"❌ Failed to fetch availability for ItemId {item_id}: {response.text}")
        return None


# Main script execution
if __name__ == "__main__":
    auth_token = login()

    if auth_token:
        # Get today's date in YYYY-MM-DD format
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Fetch both Indoor and Outdoor pool availability
        indoor_availability = check_swim_lane_availability(auth_token, today_str, 366)  # Indoor Pool
        outdoor_availability = check_swim_lane_availability(auth_token, today_str, 359)  # Outdoor Pool

        # Print the JSON responses for verification
        if indoor_availability:
            print("\n🏊 Indoor Pool Availability:")
            print(json.dumps(indoor_availability, indent=2))

        if outdoor_availability:
            print("\n🌞 Outdoor Pool Availability:")
            print(json.dumps(outdoor_availability, indent=2))
