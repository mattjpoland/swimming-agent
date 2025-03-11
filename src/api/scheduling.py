import os
import requests
import datetime
import pytz
from src.api.login import login  # Import login function
from src.constants import COMPANY_ID, CUSTOMER_ID

# Construct API URL
BASE_MAC_URL = os.getenv("BASE_MAC_URL")
SCHEDULING_URL = f"{BASE_MAC_URL}Scheduling/GetAppointmentsSchedule"

def get_appointments_schedule(token, start_date, end_date):
    """Fetch scheduled appointments for a customer within a given date range."""
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": COMPANY_ID,
        "x-customerid": CUSTOMER_ID,
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "ClubId": 2,  # Michigan Athletic Club
        "StartDate": f"{start_date}T05:00:00.000Z",
        "EndDate": f"{end_date}T05:00:00.000Z"
    }

    response = requests.post(SCHEDULING_URL, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        print("✅ Successfully retrieved scheduled appointments!")
        return response.json()
    else:
        print(f"❌ Failed to fetch appointments: {response.text}")
        return None
