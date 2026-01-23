
import requests
import json

url = "http://m.stage.ktvsky.com/vod/song/order"
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Payload from Swagger example
payload = {
    "ktvid": "105497",
    "unionid": "o6qE3twVuimSKKGHj0agds7YmiGA",
    "singer": "毛不易",
    "openid": "CweEOD6BzIIJW2c0QSOQ0yqM",
    "origin": "song",
    "musicname": "像我这样的人(HD)",
    "songid": "7573889",
    "parm": json.dumps({"vip":0,"isRecord":0,"isScore":0,"isForceJinhai":0})
}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, data=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response Headers:")
    for k, v in response.headers.items():
        print(f"  {k}: {v}")
    
    print("\nResponse Body:")
    print(response.text)
    
    try:
        json_data = response.json()
        print("\nParsed JSON:")
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
    except:
        print("\nResponse is not valid JSON")

except Exception as e:
    print(f"Error: {e}")
