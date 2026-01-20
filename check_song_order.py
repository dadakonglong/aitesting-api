import json

swagger_file = r"d:\testc\aitesting-api\Swagger_Api_H5.json"

with open(swagger_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 查找 /vod/song/order 接口的完整定义
paths = data.get("paths", {})
target_path = "/vod/song/order"

if target_path in paths:
    methods = paths[target_path]
    print(f"=== {target_path} 的完整定义 ===\n")
    print(json.dumps(methods, indent=2, ensure_ascii=False))
else:
    print(f"未找到 {target_path}")
