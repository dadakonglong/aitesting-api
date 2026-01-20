import json

def analyze():
    file_path = r"d:\testc\aitesting-api\Swagger_Api_增值项目.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    paths = data.get("paths", {})
    print(f"Total paths: {len(paths)}")
    
    results = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            headers = {}
            request_body = details.get("requestBody", {})
            content = request_body.get("content", {})
            
            # 记录所有 content-type
            all_cts = list(content.keys())
            
            # 模拟我的最新逻辑
            if method.lower() in ["post", "put", "patch"]:
                headers["Content-Type"] = "application/json"
                if content:
                    # 优先级：application/json > others
                    if "application/json" in content:
                         headers["Content-Type"] = "application/json"
                    else:
                        for ct in content.keys():
                            if ct and str(ct).lower() != "null":
                                headers["Content-Type"] = ct
                                break
            
            results.append({
                "path": path,
                "method": method.upper(),
                "all_cts": all_cts,
                "final_header": headers.get("Content-Type", "NONE")
            })
    
    # 打印结果
    print(f"{'METHOD':<8} {'PATH':<40} {'FINAL_CT':<25} {'ALL_DEFINED_CT'}")
    print("-" * 100)
    for r in results:
        print(f"{r['method']:<8} {r['path']:<40} {r['final_header']:<25} {r['all_cts']}")

if __name__ == "__main__":
    analyze()
