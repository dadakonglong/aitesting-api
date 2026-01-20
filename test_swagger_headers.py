import json

def test_parse():
    swagger_path = r"d:\testc\aitesting-api\Swagger_Api_增值项目.json"
    with open(swagger_path, 'r', encoding='utf-8') as f:
        swagger_data = json.load(f)
    
    paths = swagger_data.get("paths", {})
    results = []
    
    for path, methods in paths.items():
        path_params = methods.get("parameters", [])
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                headers = {}
                # 模拟逻辑
                request_body = details.get("requestBody", {})
                content_types = request_body.get("content", {})
                if content_types:
                    valid_cts = [k for k in content_types.keys() if k and str(k).lower() != "null"]
                    if valid_cts:
                        headers["Content-Type"] = valid_cts[0]
                elif method.lower() in ["post", "put", "patch"] and not headers.get("Content-Type"):
                    if request_body:
                        headers["Content-Type"] = "application/json"
                
                results.append(f"{method.upper()} {path}: {headers}")
    
    for r in results[:10]:
        print(r)

if __name__ == "__main__":
    test_parse()
