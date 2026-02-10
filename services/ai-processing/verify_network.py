import requests
import sys

def check(url):
    print(f"Checking {url}...")
    try:
        resp = requests.get(url, timeout=5)
        print(f"Status: {resp.status_code}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    success_ipv4 = check("http://127.0.0.1:8000/api/v1/import/supported-types")
    success_localhost = check("http://localhost:8000/api/v1/import/supported-types")
    
    if success_ipv4 and not success_localhost:
        print("\nCONCLUSION: 127.0.0.1 works but localhost fails. Frontend should use 127.0.0.1.")
    elif not success_ipv4 and not success_localhost:
        print("\nCONCLUSION: Both fail. Server might be down.")
    else:
        print("\nCONCLUSION: Both work. Issue might be CORS or Browser specific.")
