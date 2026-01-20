import json

# 检查 Swagger 文件中是否有额外的 headers 定义
swagger_file = r"d:\testc\aitesting-api\Swagger_Api_H5.json"

with open(swagger_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 查找 /vod/song/order 接口
paths = data.get("paths", {})
target_path = "/vod/song/order"

if target_path in paths:
    post_def = paths[target_path].get("post", {})
    
    print("=== 检查所有可能包含 headers 的位置 ===\n")
    
    # 1. parameters 中的 header
    print("1. parameters 中的 headers:")
    params = post_def.get("parameters", [])
    header_params = [p for p in params if p.get("in") == "header"]
    if header_params:
        for h in header_params:
            print(f"   - {h.get('name')}: {h}")
    else:
        print("   (无)")
    
    # 2. requestBody 中可能的 headers
    print("\n2. requestBody.content:")
    rb = post_def.get("requestBody", {})
    content = rb.get("content", {})
    for ct, ct_def in content.items():
        print(f"   - {ct}")
        schema = ct_def.get("schema", {})
        if "properties" in schema:
            print(f"     properties: {list(schema['properties'].keys())[:5]}...")
    
    # 3. 检查是否有 x-headers 或其他扩展字段
    print("\n3. 扩展字段 (x-*):")
    for key in post_def.keys():
        if key.startswith("x-"):
            print(f"   - {key}: {post_def[key]}")
    
    # 4. 完整的 post 定义的所有 key
    print("\n4. post 定义的所有顶层字段:")
    print(f"   {list(post_def.keys())}")
    
    # 5. 检查 responses 中的 headers
    print("\n5. responses 中的 headers:")
    responses = post_def.get("responses", {})
    for status, resp_def in responses.items():
        resp_headers = resp_def.get("headers", {})
        if resp_headers:
            print(f"   状态码 {status}:")
            for h_name, h_def in resp_headers.items():
                print(f"     - {h_name}: {h_def}")
