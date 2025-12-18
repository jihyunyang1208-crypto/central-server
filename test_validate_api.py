import requests
import json

# Use the actual token from AutoTrader
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzY1Nzk3NjY4LCJ0eXBlIjoiYWNjZXNzIn0.Du4ZAXkC-btRhQUbV-hb6eDbG802kvRw2qtA_FtZx88"

print("Testing subscription validation API...")
print(f"Token: {token[:50]}...\n")

# Test subscription validation
validate_response = requests.get(
    "http://localhost:8002/api/v1/subscriptions/validate",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Status Code: {validate_response.status_code}")
print(f"\nResponse Body:")
if validate_response.status_code == 200:
    response_data = validate_response.json()
    print(json.dumps(response_data, indent=2))
    
    # Check what AutoTrader expects
    print("\n" + "="*80)
    print("Checking response format for AutoTrader compatibility:")
    print("="*80)
    print(f"Has 'valid' key: {'valid' in response_data}")
    print(f"Has 'plan_name' key: {'plan_name' in response_data}")
    print(f"plan_name value: {response_data.get('plan_name', 'N/A')}")
else:
    print(validate_response.text)
