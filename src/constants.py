import os
import datetime
import json
from src.sql.authGateway import get_auth, get_db_connection

_BASE_MAC_URL = os.getenv("BASE_MAC_URL")
_AVAILABILITY_URL = f"{_BASE_MAC_URL}Scheduling/GetBookAvailability"
_LOGIN_URL = f"{_BASE_MAC_URL}CustomerAuth/CustomerLogin"
_COMPANY_ID = os.getenv("COMPANY_ID")

# Parse the JSON dictionary from the AUTH_DICTIONARY environment variable
auth_dict_str = os.getenv("AUTH_DICTIONARY")
_auth_dict = json.loads(auth_dict_str)

def load_context_for_authenticated_user(api_key):
    auth_entry = get_auth_by_api_key(api_key)
    if not auth_entry:
        return None

    context = {
        "API_KEY": auth_entry["api_key"],
        "USERNAME": auth_entry["username"],
        "CUSTOMER_ID": auth_entry["customer_id"],
        "ALT_CUSTOMER_ID": auth_entry["alt_customer_id"],
        "ENABLED": auth_entry["enabled"],
        "ITEMS": {},  # Add any additional context items here
    }
    return context

def get_auth_by_api_key(api_key):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_data WHERE api_key = %s", (api_key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "username": result[0],
            "api_key": result[1],
            "customer_id": result[2],
            "alt_customer_id": result[3],
            "enabled": result[4],
        }
    return None

def load_context_for_registration_pages():
    """Load context for registration pages without requiring an API key."""
    return {
        "BASE_MAC_URL": _BASE_MAC_URL,
        "AVAILABILITY_URL": _AVAILABILITY_URL,
        "LOGIN_URL": _LOGIN_URL,
        "COMPANY_ID": _COMPANY_ID,
        "TOKEN_CACHE_FILE": _TOKEN_CACHE_FILE,
        "LANES_BY_POOL": _LANES_BY_POOL,
        "ITEMS": _ITEMS,
        "APPOINTMENT_ITEMS": _APPOINTMENT_ITEMS,
        "ASSIGNED_RESOURCE_IDS": _ASSIGNED_RESOURCE_IDS,
        "RESOURCE_TYPE_IDS": _RESOURCE_TYPE_IDS,
        "DURATION_IDS": _DURATION_IDS,
        "LOCATION_SHORT_NAMES": _LOCATION_SHORT_NAMES,
        "BOOK_SELECTION_IDS": _BOOK_SELECTION_IDS,
        "LANES": _LANES,
        "TIME_SLOTS": _TIME_SLOTS
    }

_TOKEN_CACHE_FILE = "token_cache.json"  # File to store token locally

# Constants
_LANES_BY_POOL = {
    "Indoor Pool": ["Indoor Lane 1", "Indoor Lane 2", "Indoor Lane 3", "Indoor Lane 4", "Indoor Lane 5", "Indoor Lane 6"],
    "Outdoor Pool": ["Outdoor Lane 1", "Outdoor Lane 2", "Outdoor Lane 3", "Outdoor Lane 4", "Outdoor Lane 5", "Outdoor Lane 6"]
}

_ITEMS = {
    "Outdoor Pool": 359,
    "Indoor Pool": 366
}

_APPOINTMENT_ITEMS = {
    "60 Min Outdoor Lane Reservation": 364,        
    "30 Min Outdoor Lane Reservation": 359,
    "60 Min Indoor Lane Reservation": 367,
    "30 Min Indoor Lane Reservation": 366
}

_ASSIGNED_RESOURCE_IDS = {
    "60 Min Outdoor": 45,
    "30 Min Outdoor": 43,
    "60 Min Indoor": 60,
    "30 Min Indoor": 1996
}

_RESOURCE_TYPE_IDS = {
    "Outdoor Pool": 6,
    "Indoor Pool": 5
}

_DURATION_IDS = {
    "30 Min": 1,
    "60 Min": 2
}

_LOCATION_SHORT_NAMES = {
    "Indoor Pool": "Indoor",
    "Outdoor Pool": "Outdoor"
}

_BOOK_SELECTION_IDS = {
    "Indoor Lane 1": 35,
    "Indoor Lane 2": 41, 
    "Indoor Lane 3": 45,
    "Indoor Lane 4": 46,
    "Indoor Lane 5": 51,
    "Indoor Lane 6": 55,
    "Outdoor Lane 1": 16,
    "Outdoor Lane 2": 19,
    "Outdoor Lane 3": 20,
    "Outdoor Lane 4": 21,
    "Outdoor Lane 5": 22,
    "Outdoor Lane 6": 23
}

_LANES = {
    "Lane 1": 1,
    "Lane 2": 2,
    "Lane 3": 3,
    "Lane 4": 4,
    "Lane 5": 5,
    "Lane 6": 6
}

# Define correct time slots (Eastern Time)
_TIME_SLOTS = [datetime.time(hour, minute).strftime("%I:%M %p").lstrip("0")
              for hour in range(8, 22) for minute in (0, 30)]