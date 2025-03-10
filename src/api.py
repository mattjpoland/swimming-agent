import requests
import json
import os
from datetime import datetime, timezone

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    with open(config_path, 'r') as file:
        return json.load(file)

config = load_config()
LOGIN_URL = config["api_url"]
AVAILABILITY_URL = "https://www.ourclublogin.com/api/Scheduling/GetBookAvailability"
USERNAME = config["username"]
PASSWORD = config["password"]
COMPANY_ID = config["company_id"]
CUSTOMER_ID = config["customer_id"]

# Login function to get auth token
def login():
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
    
    response = requests.post(LOGIN_URL, headers=headers, json=payload, verify=False)  # Bypass SSL issues
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract the token from the 'data' dictionary
        token = data.get("data", {}).get("token")

        if token:
            print("✅ Login successful! Token retrieved.")
            return token
        else:
            print("❌ Login failed: Token not found in response.")
            return None
    else:
        print(f"❌ Login failed: {response.text}")
        return None

# Function to check swim lane availability for a specific pool (Indoor or Outdoor)
def check_swim_lane_availability(token, date_str, item_id):
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
        "ItemId": item_id,  # 🔹 Dynamically passed
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
