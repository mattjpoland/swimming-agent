import os
import requests
import datetime
import pytz
from src.api.loginGateway import login  # Import login function
import src.constants
# Construct API URL
BASE_MAC_URL = os.getenv("BASE_MAC_URL")
SCHEDULING_URL = f"{BASE_MAC_URL}Scheduling/GetAppointmentsSchedule"
BOOKING_URL = f"{BASE_MAC_URL}TransactionProcessing/BookAppointmentOnAccount"

def get_appointments_schedule(token, start_date, end_date, context):
    """Fetch scheduled appointments for a customer within a given date range."""
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": context["COMPANY_ID"],
        "x-customerid": context["CUSTOMER_ID"],
        "Authorization": f"Bearer {token}"
    }



    payload = {
        "ClubId": 2,  # Michigan Athletic Club
        "StartDate": start_date,
        "EndDate": end_date
    }

    response = requests.post(SCHEDULING_URL, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        print("✅ Successfully retrieved scheduled appointments!")
        return response.json(), response.status_code
    else:
        print(f"❌ Failed to fetch appointments: {response.text}")
        return None, response.status_code

def book_swim_lane(token, appointment_date_time, duration, location, lane, context):
    """
    Book a swim lane using the provided token.
    """
    url = BOOKING_URL
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-companyid': context["COMPANY_ID"],
        'x-customerid': str(context["CUSTOMER_ID"])
    }

    # Map the input values to the corresponding IDs and names
    resource_type_id = context["RESOURCE_TYPE_IDS"].get(location) 
    location_short_name = context["LOCATION_SHORT_NAMES"].get(location)
    appointment_item_id = context["APPOINTMENT_ITEMS"].get(f"{duration} {location_short_name} Lane Reservation")
    assigned_resource_id = context["ASSIGNED_RESOURCE_IDS"].get(f"{duration} {location_short_name}")

    book_selection_name = f"{location_short_name} {lane}"
    book_selection_id = context["BOOK_SELECTION_IDS"].get(book_selection_name)

    if not appointment_item_id or not assigned_resource_id or not book_selection_id:
        return {"error": "Invalid location or lane"}, 400

    payload = {
        "ClubId": 2,
        "LoggedInCustomerId": context["CUSTOMER_ID"],
        "PrimaryCustomerId": context["CUSTOMER_ID"],
        "AdditionalCustomerIds": [],
        "AppointmentItemId": appointment_item_id,
        "SelectedBooks": [
            {
                "Id": book_selection_id,
                "Name": book_selection_name,
                "ResourceTypeId": resource_type_id,
                "AssignedResourceId": assigned_resource_id,
                "IsAssignedResourceSelectable": True
            }
        ],
        "PackageItemId": 0,
        "PackageQuantity": 0,
        "ChangeFeeId": 0,
        "StartDate": appointment_date_time,  # ✅ Uses converted UTC timestamp
        "UserDisplayedPayNowGrandTotal": 0,
        "DisplayedAmountDueAtTimeOfService": 0,
        "CancellationAppointmentId": 0
    }

    print(f"📅 Booking swim lane for {location} {lane} for {duration} on {appointment_date_time}")
    response = requests.post(url, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        return response.json(), response.status_code
    else:
        print(f"❌ Booking request failed: {response.text}")
        return {"error": "Booking request failed"}, response.status_code

def cancel_appointment(token, appointment_id, context):
    """Cancel an appointment using a valid token."""
    url = 'https://www.ourclublogin.com/api/Scheduling/CancelAppointment'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'x-companyid': context["COMPANY_ID"],
        'x-customerid': context["CUSTOMER_ID"]
    }
    payload = {
        "AppointmentId": appointment_id
    }

    response = requests.post(url, headers=headers, json=payload, verify=False)

    if response.status_code == 200:
        print(f"✅ Successfully cancelled appointment with ID {appointment_id}!")
        return response.json(), response.status_code
    else:
        print(f"❌ Failed to cancel appointment with ID {appointment_id}: {response.text}")
        return None, response.status_code
