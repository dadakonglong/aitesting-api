import json

# 读取 Swagger 文件
with open(r"d:\testc\aitesting-api\Swagger_Api_增值项目.json", "r", encoding="utf-8") as f:
    swagger_data = json.load(f)

# 解析
apis = []
paths = swagger_data.get("paths", {})

print(f"Total paths: {len(paths)}")

for path, methods in paths.items():
    print(f"\nPath: {path}")
    print(f"Methods type: {type(methods)}")
    print(f"Methods keys: {list(methods.keys()) if isinstance(methods, dict) else 'Not a dict'}")
    
    if isinstance(methods, dict):
        for method, details in methods.items():
            print(f"  Method: {method}, Type: {type(details)}")
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                if isinstance(details, dict):
                    apis.append({
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", "")
                    })
                    print(f"    ✓ Added: {method.upper()} {path}")

print(f"\n\nTotal APIs parsed: {len(apis)}")
for api in apis:
    print(f"  - {api['method']} {api['path']}: {api['summary']}")
