import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_api_crud():
    print(f"Testing API CRUD at {BASE_URL}...")
    
    # 0. Health Check (Optional)
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"Root endpoint status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Service root not reachable: {e}") 
        # proceed anyway

    # 1. Create API
    new_api = {
        "name": "VerifyFixTest",
        "method": "POST",
        "path": "/verify/fix_" + str(requests.utils.quote("test")),
        "description": "Temporary API to verify persistence fix",
        "project_id": "verify-project"
    }
    
    print("1. Creating API...")
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/apis", json=new_api)
        if resp.status_code not in [200, 201]:
            print(f"❌ Create failed: {resp.status_code} - {resp.text}")
            return
        
        api_id = resp.json().get("id")
        print(f"✅ Created API with ID: {api_id}")
    except Exception as e:
        print(f"❌ Create request failed: {e}")
        return

    # 2. List APIs
    print("2. Listing APIs...")
    try:
        resp = requests.get(f"{BASE_URL}/api/v1/apis?project_id=verify-project")
        data = resp.json()
        apis = data.get("apis", [])
        found = any(str(api["id"]) == str(api_id) for api in apis)
        
        if found:
            print(f"✅ Found created API in list (Persistence Works!)")
        else:
            print(f"❌ API not found in list (Persistence Failed)")
            print(f"List response sample: {str(data)[:200]}...")
    except Exception as e:
        print(f"❌ List request failed: {e}")
        return

    # 3. Delete API
    print("3. Deleting API...")
    try:
        resp = requests.delete(f"{BASE_URL}/api/v1/apis/{api_id}")
        if resp.status_code == 200:
            print("✅ Deleted API")
        else:
            print(f"❌ Delete failed: {resp.status_code}")
    except Exception as e:
        print(f"❌ Delete request failed: {e}")

if __name__ == "__main__":
    test_api_crud()
