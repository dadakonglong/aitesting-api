import json

# 检查 MeterSphere 导出的 Swagger 文件
swagger_file = r"d:\testc\aitesting-api\Swagger_Api_H502.json"

try:
    with open(swagger_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    paths = data.get("paths", {})
    print(f"=== MeterSphere Swagger 文件分析 ===")
    print(f"总接口数: {sum(len([m for m in methods.keys() if m.lower() in ['get', 'post', 'put', 'delete', 'patch']]) for methods in paths.values())}\n")
    
    # 统计有 headers 定义的接口
    apis_with_headers = []
    apis_without_headers = []
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
            
            # 检查 parameters 中是否有 header
            params = details.get("parameters", [])
            header_params = [p for p in params if p.get("in") == "header"]
            
            if header_params:
                apis_with_headers.append({
                    "path": path,
                    "method": method.upper(),
                    "headers": header_params
                })
            else:
                apis_without_headers.append(f"{method.upper()} {path}")
    
    print(f"✅ 包含 headers 定义的接口: {len(apis_with_headers)}")
    if apis_with_headers:
        print("\n详细信息：")
        for api in apis_with_headers[:5]:  # 只显示前5个
            print(f"\n{api['method']} {api['path']}")
            for h in api['headers']:
                print(f"  - {h.get('name')}: {h.get('schema', {}).get('type', 'N/A')}")
        if len(apis_with_headers) > 5:
            print(f"\n... 还有 {len(apis_with_headers) - 5} 个接口")
    
    print(f"\n❌ 没有 headers 定义的接口: {len(apis_without_headers)}")
    if apis_without_headers:
        print("示例（前10个）：")
        for api in apis_without_headers[:10]:
            print(f"  - {api}")
        if len(apis_without_headers) > 10:
            print(f"  ... 还有 {len(apis_without_headers) - 10} 个")
    
    # 检查第一个接口的完整结构
    if paths:
        first_path = list(paths.keys())[0]
        first_method = [m for m in paths[first_path].keys() if m.lower() in ['get', 'post', 'put', 'delete', 'patch']][0]
        print(f"\n=== 示例接口完整结构 ===")
        print(f"{first_method.upper()} {first_path}")
        print(json.dumps(paths[first_path][first_method], indent=2, ensure_ascii=False)[:500] + "...")

except FileNotFoundError:
    print(f"❌ 文件不存在: {swagger_file}")
except Exception as e:
    print(f"❌ 错误: {e}")
