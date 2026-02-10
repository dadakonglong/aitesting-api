import requests
import urllib.parse

base_url = "http://127.0.0.1:8000"
project_id = "汇金ERP"

encoded_project_id = urllib.parse.quote(project_id)
url = f"{base_url}/api/v1/apis?project_id={encoded_project_id}&limit=10"

print(f"Requesting: {url}")

try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total APIs found: {data.get('total')}")
        apis = data.get('apis', [])
        print(f"Returned {len(apis)} APIs")
        if len(apis) > 0:
            print("First API:", apis[0]['name'], apis[0]['path'])
    else:
        print("Error:", resp.text)
except Exception as e:
    print(f"Exception: {e}")
