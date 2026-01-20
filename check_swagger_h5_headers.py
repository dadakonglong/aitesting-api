import json

# 检查 Swagger 文件中是否包含 headers 定义
swagger_file = r"d:\testc\aitesting-api\Swagger_Api_H5.json"

with open(swagger_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

paths = data.get("paths", {})

print("=== 检查 Swagger 文件中的 Headers 定义 ===\n")

# 检查是否有任何接口在 parameters 中定义了 header
has_headers = False
for path, methods in paths.items():
    for method, details in methods.items():
        if method.lower() not in ["get", "post", "put", "delete", "patch"]:
            continue
        
        # 检查 parameters 中是否有 header 类型
        params = details.get("parameters", [])
        headers_found = [p for p in params if p.get("in") == "header"]
        
        if headers_found:
            has_headers = True
            print(f"{method.upper()} {path}")
            for h in headers_found:
                print(f"  - Header: {h.get('name')} = {h.get('schema', {}).get('default', 'N/A')}")
            print()

if not has_headers:
    print("✓ 该 Swagger 文件中没有任何接口在 parameters 中定义 header")

print("\n=== 检查 requestBody 中的 Content-Type ===\n")

# 检查 POST 接口的 requestBody
for path, methods in paths.items():
    for method, details in methods.items():
        if method.lower() not in ["post", "put", "patch"]:
            continue
        
        request_body = details.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            content_types = list(content.keys())
            
            if content_types:
                print(f"{method.upper()} {path}")
                print(f"  Content-Types: {content_types}")
                print()
