from apikeys import API_KEY, API_PASS

import requests 

login_url = "https://gateway.extempo.rocks/auth/login"
login_payload = {
    "username": "koller@uchicago.edu",
    "password": API_PASS
}

login_response = requests.post(login_url, json=login_payload)

if login_response.status_code == 200:
    token = login_response.json().get("access_token")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
else:
    print("Login failed:", login_response.json())
    exit()

url = "https://gateway.extempo.rocks/docs"

payload = {
  "num_images": 5,
  "attribute": "smile",
  "beta": 1.5,
  "control_attributes": ["age", "gender"],
  "interpretable_betas": True
}

# auth = {
#   "username": "koller@uchicago.edu",
#   "password": API_PASS
# }


response = requests.post(url, json=payload)

print(response.status_code)
print(response.json())


# {
#   "num_images": 0,
#   "attribute": "string",
#   "beta": 0,
#   "control_attributes": [
#     "string"
#   ],
#   "interpretable_betas": true
# }

