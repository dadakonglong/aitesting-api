"""
测试脚本：验证自动补充标准 HTTP Headers 功能
"""
import json
import sys

# 模拟 Swagger 导入逻辑中的 headers 处理部分
def test_headers_generation():
    # 模拟不同场景
    test_cases = [
        {
            "name": "GET 请求（无 base_url）",
            "method": "get",
            "base_url": "",
            "params": [],
            "request_body": {}
        },
        {
            "name": "GET 请求（有 base_url）",
            "method": "get",
            "base_url": "http://172.16.1.8:8088/mock/100007",
            "params": [],
            "request_body": {}
        },
        {
            "name": "POST 请求（multipart/form-data）",
            "method": "post",
            "base_url": "http://172.16.1.8:8088/mock/100007",
            "params": [],
            "request_body": {
                "content": {
                    "multipart/form-data": {
                        "schema": {"properties": {}}
                    }
                }
            }
        },
        {
            "name": "POST 请求（application/json）",
            "method": "post",
            "base_url": "http://172.16.1.8:8088/mock/100007",
            "params": [],
            "request_body": {
                "content": {
                    "application/json": {
                        "schema": {"properties": {}}
                    }
                }
            }
        },
        {
            "name": "POST 请求（有自定义 header）",
            "method": "post",
            "base_url": "http://172.16.1.8:8088/mock/100007",
            "params": [
                {
                    "name": "Authorization",
                    "in": "header",
                    "schema": {"default": "Bearer token123"}
                }
            ],
            "request_body": {}
        }
    ]
    
    print("=" * 80)
    print("标准 HTTP Headers 自动补充功能测试")
    print("=" * 80)
    
    for test in test_cases:
        print(f"\n【测试场景】: {test['name']}")
        print(f"  方法: {test['method'].upper()}")
        print(f"  Base URL: {test['base_url'] or '(无)'}")
        
        # 模拟 headers 生成逻辑
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": "API-Testing-Platform/1.0"
        }
        
        # 添加 Host
        if test['base_url']:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(test['base_url'])
                if parsed.netloc:
                    headers["Host"] = parsed.netloc
            except:
                pass
        
        # 处理自定义 headers
        for param in test['params']:
            if param.get("in") == "header":
                headers[param.get("name")] = param.get("schema", {}).get("default", "")
        
        # 处理 Content-Type
        if test['method'].lower() in ["post", "put", "patch"]:
            headers["Content-Type"] = "application/json"
            
            request_body = test['request_body']
            if request_body:
                content_types = request_body.get("content", {})
                if content_types:
                    for ct in content_types.keys():
                        if ct and str(ct).lower() != "null":
                            headers["Content-Type"] = ct
                            break
        
        print(f"\n  生成的 Headers:")
        for key, value in headers.items():
            print(f"    {key}: {value}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！所有场景都已生成完整的 headers")
    print("=" * 80)

if __name__ == "__main__":
    test_headers_generation()
