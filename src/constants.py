import os
import datetime

BASE_MAC_URL = os.getenv("BASE_MAC_URL")
AVAILABILITY_URL = f"{BASE_MAC_URL}Scheduling/GetBookAvailability"
LOGIN_URL = f"{BASE_MAC_URL}CustomerAuth/CustomerLogin"

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
COMPANY_ID = os.getenv("COMPANY_ID")
CUSTOMER_ID = os.getenv("CUSTOMER_ID")
ALT_CUSTOMER_ID = os.getenv("ALT_CUSTOMER_ID")
API_KEY = os.getenv("API_KEY")

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

APPOINTMENT_ITEMS = {
    "60 Min Outdoor Lane Reservation": 364,        
    "30 Min Outdoor Lane Reservation": 359,
    "60 Min Indoor Lane Reservation": 367,
    "30 Min Indoor Lane Reservation": 366
}

ASSIGNED_RESOURCE_IDS = {
    "60 Min Outdoor": 45,
    "30 Min Outdoor": 43,
    "60 Min Indoor": 60,
    "30 Min Indoor": 1996
}

RESOURCE_TYPE_IDS = {
    "Outdoor Pool": 6,
    "Indoor Pool": 5
}

DURATION_IDS = {
    "30 Min": 1,
    "60 Min": 2
}

LOCATION_SHORT_NAMES = {
    "Indoor Pool": "Indoor",
    "Outdoor Pool": "Outdoor"
}

BOOK_SELECTION_IDS = {
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

LANES = {
    "Lane 1": 1,
    "Lane 2": 2,
    "Lane 3": 3,
    "Lane 4": 4,
    "Lane 5": 5,
    "Lane 6": 6
}

# Define correct time slots (Eastern Time)
TIME_SLOTS = [datetime.time(hour, minute).strftime("%I:%M %p").lstrip("0")
              for hour in range(8, 22) for minute in (0, 30)]