#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复场景执行500错误的脚本

问题分析:
从诊断结果看,发现了一个严重的配置错误:
- 步骤1(登录接口)的param_mappings配置为: 从步骤1的data.token -> headers.Authorization
- 这是一个自引用,步骤1依赖自己的返回结果,这是不可能的!
- 正确的应该是: 步骤2/3/4依赖步骤1的token

这导致:
1. 步骤1执行时,试图从自己(还未执行)获取token -> 失败或为空
2. 步骤2/3/4没有正确配置token映射,导致Authorization header缺失或错误
3. 服务器因为缺少有效token返回500错误

解决方案:
1. 移除步骤1的错误自引用映射
2. 为步骤2/3/4正确配置token映射
3. 确保token提取路径正确(data.token)
"""

import sqlite3
import json

DB_PATH = "data/apis.db"

def fix_scenario_mappings():
    print("=" * 80)
    print("🔧 修复场景执行500错误")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 查找最新的场景
    c.execute("""
        SELECT id, name, test_case_id 
        FROM scenarios 
        ORDER BY id DESC 
        LIMIT 1
    """)
    scenario = c.fetchone()
    
    if not scenario:
        print("❌ 没有找到场景")
        conn.close()
        return
    
    scenario_id = scenario['id']
    test_case_id = scenario['test_case_id']
    
    print(f"\n🎯 修复场景: {scenario['name']} (ID: {scenario_id})")
    print(f"   测试用例ID: {test_case_id}")
    
    # 获取测试用例步骤
    c.execute("SELECT steps FROM test_cases WHERE id = ?", (test_case_id,))
    case = c.fetchone()
    
    if not case:
        print(f"❌ 找不到测试用例 {test_case_id}")
        conn.close()
        return
    
    steps = json.loads(case['steps'])
    print(f"\n📝 原始步骤数量: {len(steps)}")
    
    # 分析并修复
    print("\n🔍 分析问题:")
    print("-" * 80)
    
    fixed = False
    
    for i, step in enumerate(steps, 1):
        print(f"\n步骤 {i}: {step.get('api_method')} {step.get('api_path')}")
        
        param_mappings = step.get('param_mappings', [])
        
        if i == 1:  # 登录接口
            # 检查是否有错误的自引用
            if param_mappings:
                print(f"  ⚠️  发现步骤1有参数映射(不应该有):")
                for mapping in param_mappings:
                    print(f"     - 从步骤{mapping.get('from_step')}的{mapping.get('from_field')} -> {mapping.get('to_type', 'params')}.{mapping.get('to_field')}")
                
                # 移除步骤1的所有映射
                step['param_mappings'] = []
                print(f"  ✅ 已移除步骤1的错误映射")
                fixed = True
        
        else:  # 其他接口
            # 检查是否需要token
            headers = step.get('headers', {})
            needs_token = any('token' in str(v).lower() or 'authorization' in k.lower() 
                            for k, v in headers.items())
            
            if needs_token:
                print(f"  ℹ️  步骤{i}需要token")
                
                # 检查是否已有正确的token映射
                has_token_mapping = False
                for mapping in param_mappings:
                    if (mapping.get('from_step') == 1 and 
                        mapping.get('to_type') == 'headers' and 
                        mapping.get('to_field', '').lower() == 'authorization'):
                        has_token_mapping = True
                        print(f"  ✅ 已有token映射: {mapping}")
                        break
                
                if not has_token_mapping:
                    print(f"  ⚠️  缺少token映射,添加中...")
                    # 添加正确的token映射
                    token_mapping = {
                        "from_step": 1,
                        "from_field": "data.token",
                        "to_field": "Authorization",
                        "to_type": "headers"
                    }
                    step['param_mappings'].append(token_mapping)
                    print(f"  ✅ 已添加token映射")
                    fixed = True
    
    if not fixed:
        print("\n✅ 未发现需要修复的问题")
        conn.close()
        return
    
    # 保存修复后的步骤
    print("\n" + "=" * 80)
    print("💾 保存修复...")
    print("-" * 80)
    
    c.execute("""
        UPDATE test_cases 
        SET steps = ? 
        WHERE id = ?
    """, (json.dumps(steps, ensure_ascii=False), test_case_id))
    
    conn.commit()
    
    print(f"✅ 已更新测试用例 {test_case_id}")
    
    # 显示修复后的配置
    print("\n📋 修复后的步骤配置:")
    print("-" * 80)
    
    for i, step in enumerate(steps, 1):
        print(f"\n步骤 {i}: {step.get('api_method')} {step.get('api_path')}")
        param_mappings = step.get('param_mappings', [])
        if param_mappings:
            print(f"  参数映射:")
            for mapping in param_mappings:
                print(f"    - 从步骤{mapping.get('from_step')}的{mapping.get('from_field')} -> {mapping.get('to_type', 'params')}.{mapping.get('to_field')}")
        else:
            print(f"  无参数映射")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 修复完成!")
    print("=" * 80)
    print("\n💡 下一步:")
    print("  1. 重新执行场景测试")
    print("  2. 检查第1个接口的响应,确认token字段路径是否为 data.token")
    print("  3. 如果token路径不同,需要手动调整 from_field 配置")
    print("  4. 确认服务器API的Authorization格式要求(是否需要'Bearer '前缀)")

def show_login_response():
    """显示登录接口的实际响应,帮助确认token路径"""
    print("\n" + "=" * 80)
    print("🔍 查看登录接口的实际响应")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 查找最近的执行记录
    c.execute("""
        SELECT results 
        FROM executions 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    exec_rec = c.fetchone()
    if not exec_rec:
        print("❌ 没有找到执行记录")
        conn.close()
        return
    
    results = json.loads(exec_rec['results'])
    
    if not results:
        print("❌ 执行记录为空")
        conn.close()
        return
    
    # 显示第1步(登录)的响应
    step1 = results[0]
    print(f"\n步骤1响应 (状态码: {step1.get('status_code')}):")
    print("-" * 80)
    
    response = step1.get('response', {})
    print(json.dumps(response, ensure_ascii=False, indent=2))
    
    # 尝试提取token
    print("\n🔍 Token提取分析:")
    print("-" * 80)
    
    if isinstance(response, dict):
        # 常见的token路径
        token_paths = [
            ('data.token', lambda r: r.get('data', {}).get('token')),
            ('token', lambda r: r.get('token')),
            ('data.accessToken', lambda r: r.get('data', {}).get('accessToken')),
            ('accessToken', lambda r: r.get('accessToken')),
            ('data.access_token', lambda r: r.get('data', {}).get('access_token')),
            ('access_token', lambda r: r.get('access_token')),
        ]
        
        for path, extractor in token_paths:
            try:
                token = extractor(response)
                if token:
                    print(f"✅ 在路径 '{path}' 找到token:")
                    print(f"   {token[:50]}..." if len(str(token)) > 50 else f"   {token}")
            except:
                pass
    
    conn.close()

if __name__ == "__main__":
    fix_scenario_mappings()
    show_login_response()
