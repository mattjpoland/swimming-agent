import requests
import json

def login_with_credentials(username, password, context):
    """Fetch an authentication token using provided username and password, return the full JSON response."""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "x-companyid": context["COMPANY_ID"],
    }

    payload = {
        "UserLogin": username,
        "Pswd": password
    }

    print(f"🔍 Logging in via: {context['LOGIN_URL']}")

    response = requests.post(context["LOGIN_URL"], headers=headers, json=payload, verify=False)

    print(f"🔍 Response Status Code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            print("❌ Error: Response is not valid JSON.")
            return None
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    # Example context for testing
    context = {
        "LOGIN_URL": "https://example.com/login",
        "COMPANY_ID": "12345",
        "CUSTOMER_ID": "67890"
    }
    username = "user"
    password = "pass"
    full_response = login_with_credentials(username, password, context)
    print(full_response)