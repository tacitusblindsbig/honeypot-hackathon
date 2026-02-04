import requests
import os

# PASTE YOUR NEW GOOGLE KEY HERE
API_KEY = "AIzaSyC3nqVdpoLbB0r8kKszbSkMT6HIedbpTdM"

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print("\n✅ AVAILABLE MODELS FOR YOUR KEY:")
        for m in models:
            if 'generateContent' in m['supportedGenerationMethods']:
                print(f"- {m['name']}")
    else:
        print(f"\n❌ ERROR: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Connection Error: {e}")