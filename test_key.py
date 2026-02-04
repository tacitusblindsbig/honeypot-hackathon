import requests
import os

# REPLACE THIS WITH YOUR ACTUAL API KEY FOR TESTING
API_KEY = "AIzaSyC3nqVdpoLbB0r8kKszbSkMT6HIedbpTdM"

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
payload = {
    "contents": [{"parts": [{"text": "Say hello"}]}]
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")