import requests
import sys

def verify():
    url = "http://127.0.0.1:8000/api/v1/import/supported-types"
    print(f"Checking {url}...")
    try:
        resp = requests.get(url, timeout=5)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("Response:", resp.json())
            print("✅ Import router is mounted!")
            return True
        elif resp.status_code == 404:
            print("❌ Endpoint not found (404). Router not mounted.")
            return False
        else:
            print(f"❌ Unexpected status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please check if the server is running on port 8000.")
        return False

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
