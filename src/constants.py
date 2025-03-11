import os
import datetime

BASE_MAC_URL = os.getenv("BASE_MAC_URL")
AVAILABILITY_URL = f"{BASE_MAC_URL}Scheduling/GetBookAvailability"
LOGIN_URL = f"{BASE_MAC_URL}CustomerAuth/CustomerLogin"

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
COMPANY_ID = os.getenv("COMPANY_ID")
CUSTOMER_ID = os.getenv("CUSTOMER_ID")

TOKEN_CACHE_FILE = "token_cache.json"  # File to store token locally

# Constants
LANES_BY_POOL = {
    "Indoor Pool": ["Indoor Lane 1", "Indoor Lane 2", "Indoor Lane 3", "Indoor Lane 4", "Indoor Lane 5", "Indoor Lane 6"],
    "Outdoor Pool": ["Outdoor Lane 1", "Outdoor Lane 2", "Outdoor Lane 3", "Outdoor Lane 4", "Outdoor Lane 5", "Outdoor Lane 6"]
}

ITEMS = {
    "Outdoor Pool": 359,
    "Indoor Pool": 366
}

# Define correct time slots (Eastern Time)
TIME_SLOTS = [datetime.time(hour, minute).strftime("%I:%M %p").lstrip("0")
              for hour in range(8, 22) for minute in (0, 30)]