import requests
import json

def get_family_members(token, context):
    """Fetch family members using the provided context."""
    url = f"{context['BASE_MAC_URL']}FamilyMember/GetFamilyMembers"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-companyid": context["COMPANY_ID"],
        "x-customerid": context["CUSTOMER_ID"],
        "Cookie": "_gid=GA1.2.551022566.1742011962; coid=510726; _ga_LDP16G2K25=GS1.1.1742011962.1.1.1742012338.0.0.0; _ga=GA1.2.632360688.1742011962; _gat_gtag_UA_59836932_11=1"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            print("Error: Response is not valid JSON.")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    # Example context for testing
    context = {
        "BASE_MAC_URL": "https://www.ourclublogin.com/api/",
        "API_KEY": "your_api_key_here",
        "COMPANY_ID": "510726",
        "CUSTOMER_ID": "8507"
    }
    token = "your_token_here"
    family_members = get_family_members(token, context)
    print(family_members)