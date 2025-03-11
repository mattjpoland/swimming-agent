import requests
import os
from src.constants import COMPANY_ID, CUSTOMER_ID, AVAILABILITY_URL


def check_swim_lane_availability(token, date_str, item_id):
    """Fetch swim lane availability using a valid token."""
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
