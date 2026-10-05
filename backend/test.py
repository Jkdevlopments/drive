import requests

url = "http://localhost:8000/auth/login"

data = {
    "email": "a@gmail.com",
    "password": "1234"
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())
print(response.cookies)