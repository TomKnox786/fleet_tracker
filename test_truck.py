import requests

url = "http://127.0.0.1:5000/update_location"

data = {
    "truck_id": "TRUCK_001",
    "latitude": -26.2030,
    "longitude": 29.0500
}

response = requests.post(url, json=data)

print(response.json())