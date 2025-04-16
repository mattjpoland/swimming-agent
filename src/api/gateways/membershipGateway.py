import requests
import logging
import json
import os

def get_member_information(context):
    """
    Retrieves member information including Member ID (used as barcode) using the ManageProfile/GetMemberInformation API.
    
    Args:
        context (dict): A dictionary containing authentication information including token
    
    Returns:
        dict: The member information response or None if the request fails
    """
    url = "https://www.ourclublogin.com/api/ManageProfile/GetMemberInformation"
    
    # Prepare headers using the token from context
    token = context.get("TOKEN")
    if not token:
        logging.error("❌ No token found in context")
        return None
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-companyid": context.get("COMPANY_ID"),
        "x-customerid": context.get("CUSTOMER_ID"),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    logging.info(f"🔍 Getting member information from: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        logging.info(f"🔍 Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logging.debug(f"🔍 Member info data: {data}")
                return data
            except json.JSONDecodeError:
                logging.error("❌ Error decoding JSON response from member info API")
                return None
        else:
            logging.error(f"❌ Failed to get member information: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"❌ Exception while getting member information: {str(e)}")
        return None