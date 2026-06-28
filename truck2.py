import requests

url = "http://127.0.0.1:5000/update_location"

data = {
    "truck_id": "TRUCK_002",
    "latitude": -15.3875,
    "longitude": 28.3228
}

response = requests.post(url, json=data)

print(response.json())