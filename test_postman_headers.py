"""
测试Postman导入的headers提取逻辑
"""
import json

# 模拟Postman Collection中的一个请求
postman_item = {
    "name": "测试接口",
    "request": {
        "method": "POST",
        "header": [
            {
                "key": "Content-Type",
                "value": "application/json",
                "type": "text"
            },
            {
                "key": "Authorization",
                "value": "Bearer token123",
                "type": "text"
            },
            {
                "key": "X-Custom-Header",
                "value": "custom-value",
                "type": "text",
                "disabled": False
            },
            {
                "key": "Disabled-Header",
                "value": "should-not-appear",
                "type": "text",
                "disabled": True  # 这个应该被忽略
            }
        ],
        "url": {
            "raw": "https://api.example.com/test",
            "protocol": "https",
            "host": ["api", "example", "com"],
            "path": ["test"]
        }
    }
}

# 提取headers的逻辑(复制自main_sqlite.py)
request = postman_item.get('request', {})
headers = {}

for header in request.get('header', []):
    if not header.get('disabled', False):
        headers[header.get('key')] = header.get('value', '')

print("提取的headers:")
print(json.dumps(headers, indent=2, ensure_ascii=False))

# 预期结果
expected = {
    "Content-Type": "application/json",
    "Authorization": "Bearer token123",
    "X-Custom-Header": "custom-value"
}

print("\n预期的headers:")
print(json.dumps(expected, indent=2, ensure_ascii=False))

print("\n提取是否正确:", headers == expected)
