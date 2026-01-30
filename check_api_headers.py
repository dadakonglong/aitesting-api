#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查导入的API是否包含完整的headers信息
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def check_api_headers():
    print("=" * 80)
    print("🔍 检查导入的API headers信息")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 检查汇金ERP项目的API
    print("\n📚 汇金ERP项目的API headers:")
    
    c.execute("""
        SELECT path, method, headers, parameters, request_body 
        FROM apis 
        WHERE project_id = '汇金ERP' 
        ORDER BY path
    """)
    
    apis = c.fetchall()
    
    if not apis:
        print("   ❌ 没有找到汇金ERP的API")
        conn.close()
        return
    
    print(f"   找到 {len(apis)} 个API\n")
    
    for api in apis:
        path = api['path']
        method = api['method']
        headers = api['headers']
        parameters = api['parameters']
        request_body = api['request_body']
        
        print(f"📋 {method} {path}")
        
        # 检查headers
        if headers:
            try:
                headers_data = json.loads(headers) if isinstance(headers, str) else headers
                if headers_data:
                    print(f"   📤 Headers: {len(headers_data)}个")
                    # 只显示关键headers
                    key_headers = ['Authorization', 'Content-Type', 'X-Employee-Id', 'X-Venue-Id', 'X-Mac']
                    for key in key_headers:
                        if key in headers_data:
                            print(f"      ✅ {key}")
                else:
                    print(f"   📤 Headers: 空对象")
            except:
                print(f"   📤 Headers: 解析失败")
        else:
            print(f"   📤 Headers: 无")
        
        print()
    
    # 2. 检查AI生成时是否使用了这些信息
    print("=" * 80)
    print("🤖 检查AI生成场景时的API使用:")
    print("-" * 80)
    
    # 获取最新的测试用例
    c.execute("""
        SELECT id, name, steps 
        FROM test_cases 
        WHERE project_id = '汇金ERP' 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    latest_case = c.fetchone()
    
    if latest_case:
        steps = json.loads(latest_case['steps'])
        
        print(f"\n📋 最新测试用例: {latest_case['name']} (ID: {latest_case['id']})")
        
        for i, step in enumerate(steps, 1):
            api_path = step.get('api_path')
            api_method = step.get('api_method')
            step_headers = step.get('headers', {})
            
            print(f"\n   步骤{i}: {api_method} {api_path}")
            
            # 查找对应的原始API
            c.execute("""
                SELECT headers, parameters 
                FROM apis 
                WHERE project_id = '汇金ERP' 
                AND path = ? AND method = ?
            """, (api_path, api_method))
            
            original_api = c.fetchone()
            
            if original_api:
                original_headers = original_api['headers']
                
                print(f"   📤 生成的headers ({len(step_headers)}个):")
                for key, value in step_headers.items():
                    print(f"      {key}: {value}")
                
                if original_headers:
                    try:
                        orig_headers_data = json.loads(original_headers) if isinstance(original_headers, str) else original_headers
                        if orig_headers_data:
                            print(f"   📚 原始API的headers ({len(orig_headers_data)}个):")
                            for key, value in orig_headers_data.items():
                                if key not in step_headers:
                                    print(f"      ❌ 缺失: {key}: {value}")
                                else:
                                    print(f"      ✅ 已有: {key}")
                        else:
                            print(f"   📚 原始API headers: 空")
                    except:
                        print(f"   📚 原始API headers: {original_headers}")
                else:
                    print(f"   📚 原始API headers: 无")
            else:
                print(f"   ⚠️  找不到对应的原始API")
    
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"💡 分析结论:")
    print("=" * 80)
    print("""
如果导入的API包含完整的headers，但生成的场景缺少这些headers，
可能的原因：

1. AI生成时没有使用原始API的headers信息
2. AI prompt没有指导如何使用原始headers
3. 生成逻辑只关注了参数映射，忽略了原始headers

解决方案：
1. 改进AI prompt，让它使用原始API的headers
2. 在生成场景时，自动继承原始API的headers
3. 添加必需headers的自动补全逻辑
    """)

if __name__ == "__main__":
    check_api_headers()