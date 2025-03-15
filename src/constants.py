import os
import datetime
import json

_BASE_MAC_URL = os.getenv("BASE_MAC_URL")
_AVAILABILITY_URL = f"{_BASE_MAC_URL}Scheduling/GetBookAvailability"
_LOGIN_URL = f"{_BASE_MAC_URL}CustomerAuth/CustomerLogin"
_COMPANY_ID = os.getenv("COMPANY_ID")

# Parse the JSON dictionary from the AUTH_DICTIONARY environment variable
auth_dict_str = os.getenv("AUTH_DICTIONARY")
_auth_dict = json.loads(auth_dict_str)

def get_api_values(api_key):
    for name, api_values in _auth_dict.items():
        if api_values["API_KEY"] == api_key:
            print(f"Loading context for user: {name}")
            return {
                "API_KEY": api_key,
                "USERNAME": api_values["USERNAME"],
                "PASSWORD": api_values["PASSWORD"],
                "CUSTOMER_ID": api_values["CUSTOMER_ID"],
                "ALT_CUSTOMER_ID": api_values["ALT_CUSTOMER_ID"],
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
                "TIME_SLOTS": _TIME_SLOTS,
                "NAME": name
            }
    raise ValueError("Invalid API_KEY provided")

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