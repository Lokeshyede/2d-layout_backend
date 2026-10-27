import requests

payload = {
  "customer": {
    "customerName": "Test Customer",
    "ownerName": "Test Owner",
    "mobileNumber": "9876543210",
    "whatsAppNumber": "9876543210",
    "email": "test@test.com",
    "storeAddress": "123 Test St",
    "city": "Test City",
    "state": "Test State",
    "pincode": "123456"
  },
  "store": {
    "storeName": "Test Store",
    "storeType": "Supermarket",
    "storeArea": "1000",
    "approxWidth": "20",
    "approxHeight": "50",
    "unit": "Feet"
  },
  "survey": {
    "surveyDate": "2026-09-02",
    "salesmanName": "Test Salesman",
    "siteContactPerson": "Test Contact",
    "remarks": "Test Remarks",
    "specialRequirements": "None"
  }
}

try:
    response = requests.post("http://127.0.0.1:8000/api/surveys", json=payload)
    print("Status:", response.status_code)
    print("Body:", response.json())
except Exception as e:
    print("Failed:", e)
