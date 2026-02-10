import requests
import json
import traceback

base_url = "http://127.0.0.1:8000"

def test_execution(steps):
    url = f"{base_url}/api/v1/executions"
    payload = {
        "steps": steps,
        "environment": "test",
        "base_url": "http://httpbin.org" # harmless target
    }
    print(f"Testing with payload: {json.dumps(payload, indent=2)}")
    try:
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        try:
            print("Response:", resp.json())
        except:
            print("Response text:", resp.text)
    except Exception as e:
        print("Request failed:", e)

# Scenario 1: Valid simple execution
print("\n--- Scenario 1: Valid execution ---")
test_execution([
    {"api_method": "GET", "api_path": "/get", "params": {"q": "hello"}}
])

# Scenario 2: Params as list (suspected cause)
print("\n--- Scenario 2: Params as list ---")
test_execution([
    {"api_method": "POST", "api_path": "/post", "params": [{"key": "value"}]}
])

# Scenario 3: Params with integer keys?
print("\n--- Scenario 3: Params with integer keys ---")
test_execution([
    {"api_method": "POST", "api_path": "/post", "params": {0: "value"}}
])

# Scenario 4: URL Params as list of descriptors (The actual crash case)
print("\n--- Scenario 4: URL Params as list of descriptors ---")
test_execution([
    {
        "api_method": "GET", 
        "api_path": "/get", 
        "url_params": [{"name": "ktvid", "in": "query", "type": "string"}]
    }
])

