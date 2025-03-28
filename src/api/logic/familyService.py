from src.web.gateways.webFamilyGateway import get_family_members
from src.api.gateways.loginGateway import login_via_context
import logging

def get_family_members_action(context):
    token = login_via_context(context)
    if not token:
        return {}
    
    """Fetch and process family members using the provided context."""
    family_members = get_family_members(token, context)
    
    if family_members is None:
        return None
    
    # Trim the response to include only Id and DisplayName
    trimmed_family_members = [
        {"Id": member["Id"], "DisplayName": member["DisplayName"]}
        for member in family_members
    ]
    
    return trimmed_family_members

# Example usage
if __name__ == "__main__":
    # Example context for testing
    context = {
        "BASE_MAC_URL": "https://www.ourclublogin.com/api/",
        "API_KEY": "your_api_key_here",
        "COMPANY_ID": "510726",
        "CUSTOMER_ID": "8507"
    }
    family_members = get_family_members_action(context)
    print(family_members)