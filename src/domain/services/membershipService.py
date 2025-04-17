from src.domain.gateways.membershipGateway import get_member_information
from src.domain.gateways.loginGateway import login_via_context
import logging

def get_barcode_id_action(context):
    """
    Get the barcode ID (Member ID) for the authenticated user.
    
    Args:
        context (dict): The authentication context with username, password, etc.
    
    Returns:
        tuple: (response_dict, status_code)
    """
    # Ensure we have a valid token
    if not context.get("TOKEN"):
        logging.info("No token found in context, attempting to login")
        token = login_via_context(context)
        if not token:
            return {"error": "Authentication failed"}, 401
        context["TOKEN"] = token
    
    # Get member information
    member_info = get_member_information(context)
    
    if not member_info:
        return {"error": "Failed to retrieve member information"}, 500
    
    # Extract Member ID (which is used as the barcode) from the member information
    barcode_id = member_info.get("MemberID")
    
    if not barcode_id:
        return {"error": "Member ID (barcode) not found in member information"}, 404
    
    return {"barcode_id": barcode_id}, 200