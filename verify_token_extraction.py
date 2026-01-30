#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Token提取和传递机制
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def verify_token_extraction():
    print("=" * 80)
    print("🔍 验证Token提取和传递机制")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 获取最新的执行记录
    c.execute("""
        SELECT id, test_case_id, status, results, created_at 
        FROM executions 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    execution = c.fetchone()
    
    if not execution:
        print("❌ 没有找到执行记录")
        conn.close()
        return
    
    print(f"\n📊 执行记录 ID: {execution['id']}")
    print(f"   测试用例 ID: {execution['test_case_id']}")
    print(f"   状态: {execution['status']}")
    print(f"   时间: {execution['created_at']}")
    
    results = json.loads(execution['results'])
    
    print("\n" + "=" * 80)
    print("🔬 详细分析每个步骤")
    print("=" * 80)
    
    # 分析步骤1（登录）
    if len(results) > 0:
        step1 = results[0]
        print(f"\n📝 步骤1 (登录接口):")
        print(f"   URL: {step1.get('url')}")
        print(f"   方法: {step1.get('method')}")
        print(f"   状态码: {step1.get('status_code')}")
        print(f"   成功: {step1.get('success')}")
        
        # 检查请求头
        request_headers = step1.get('request_headers', {})
        print(f"\n   📤 请求头:")
        if request_headers:
            for key, value in request_headers.items():
                print(f"      {key}: {value}")
        else:
            print(f"      (空)")
        
        # 检查响应
        response = step1.get('response', {})
        print(f"\n   📥 响应分析:")
        
        if isinstance(response, dict):
            # 检查是否有token
            token_found = False
            token_value = None
            token_path = None
            
            # 尝试多种常见路径
            token_paths = [
                ('data.token', lambda r: r.get('data', {}).get('token')),
                ('token', lambda r: r.get('token')),
                ('data.accessToken', lambda r: r.get('data', {}).get('accessToken')),
                ('accessToken', lambda r: r.get('accessToken')),
            ]
            
            for path, extractor in token_paths:
                try:
                    token = extractor(response)
                    if token:
                        token_found = True
                        token_value = token
                        token_path = path
                        break
                except:
                    pass
            
            if token_found:
                print(f"      ✅ 找到token")
                print(f"      路径: {token_path}")
                print(f"      值: {str(token_value)[:50]}..." if len(str(token_value)) > 50 else f"      值: {token_value}")
            else:
                print(f"      ❌ 未找到token")
                print(f"      响应结构: {json.dumps(response, ensure_ascii=False, indent=8)[:500]}...")
        else:
            print(f"      ⚠️  响应不是JSON格式")
    
    # 分析步骤2（第一个业务接口）
    if len(results) > 1:
        step2 = results[1]
        print(f"\n" + "-" * 80)
        print(f"📝 步骤2 (业务接口):")
        print(f"   URL: {step2.get('url')}")
        print(f"   方法: {step2.get('method')}")
        print(f"   状态码: {step2.get('status_code')}")
        print(f"   成功: {step2.get('success')}")
        
        # 检查请求头 - 关键！
        request_headers = step2.get('request_headers', {})
        print(f"\n   📤 请求头 (关键检查):")
        
        has_auth = False
        auth_value = None
        
        if request_headers:
            for key, value in request_headers.items():
                print(f"      {key}: {value}")
                if key.lower() == 'authorization':
                    has_auth = True
                    auth_value = value
        else:
            print(f"      (空)")
        
        # 分析Authorization
        print(f"\n   🔐 Authorization分析:")
        if has_auth:
            if auth_value and 'Bearer' in auth_value:
                # 检查是否是占位符
                if '{{' in auth_value or 'token_from_step' in auth_value:
                    print(f"      ❌ Authorization是占位符，未被替换")
                    print(f"      值: {auth_value}")
                    print(f"      原因: param_mappings配置错误或token提取失败")
                else:
                    print(f"      ✅ Authorization已正确设置")
                    print(f"      值: {auth_value[:50]}..." if len(auth_value) > 50 else f"      值: {auth_value}")
            else:
                print(f"      ⚠️  Authorization格式异常")
                print(f"      值: {auth_value}")
        else:
            print(f"      ❌ 缺少Authorization header")
            print(f"      这会导致服务器返回401或500错误")
        
        # 检查响应
        response = step2.get('response', {})
        print(f"\n   📥 响应:")
        
        if isinstance(response, dict):
            code = response.get('code')
            message = response.get('message')
            
            if code == 500 or code == 4200:
                print(f"      ❌ 服务器错误")
                print(f"      错误码: {code}")
                print(f"      错误信息: {message}")
                
                # 分析错误原因
                if '门店权限' in str(message) or '无效' in str(message):
                    print(f"\n      💡 可能原因:")
                    print(f"         1. Token未正确传递")
                    print(f"         2. Token已过期")
                    print(f"         3. Token格式错误")
            else:
                print(f"      ✅ 响应正常")
                print(f"      code: {code}")
                print(f"      message: {message}")
        else:
            print(f"      响应: {str(response)[:200]}...")
    
    # 获取测试用例配置
    print("\n" + "=" * 80)
    print("⚙️  测试用例配置检查")
    print("=" * 80)
    
    c.execute("SELECT steps FROM test_cases WHERE id = ?", (execution['test_case_id'],))
    case = c.fetchone()
    
    if case:
        steps = json.loads(case['steps'])
        
        # 检查步骤2的param_mappings
        if len(steps) > 1:
            step2_config = steps[1]
            print(f"\n📋 步骤2的配置:")
            print(f"   API: {step2_config.get('api_method')} {step2_config.get('api_path')}")
            
            param_mappings = step2_config.get('param_mappings', [])
            print(f"\n   参数映射 (param_mappings):")
            
            if param_mappings:
                has_token_mapping = False
                for mapping in param_mappings:
                    from_step = mapping.get('from_step')
                    from_field = mapping.get('from_field')
                    to_field = mapping.get('to_field')
                    to_type = mapping.get('to_type', 'params')
                    
                    print(f"      - 从步骤{from_step}的{from_field} -> {to_type}.{to_field}")
                    
                    if to_type == 'headers' and to_field.lower() == 'authorization':
                        has_token_mapping = True
                
                if has_token_mapping:
                    print(f"\n   ✅ 已配置token映射")
                else:
                    print(f"\n   ⚠️  未配置token映射到headers.Authorization")
            else:
                print(f"      (空)")
                print(f"\n   ❌ 缺少参数映射配置")
                print(f"   这是导致500错误的主要原因！")
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 诊断总结")
    print("=" * 80)
    
    issues = []
    
    # 检查步骤1是否成功
    if len(results) > 0 and not results[0].get('success'):
        issues.append("步骤1（登录）失败")
    
    # 检查步骤1是否返回token
    if len(results) > 0:
        response = results[0].get('response', {})
        if isinstance(response, dict):
            token = response.get('data', {}).get('token')
            if not token:
                issues.append("步骤1未返回token")
    
    # 检查步骤2是否有Authorization
    if len(results) > 1:
        headers = results[1].get('request_headers', {})
        auth = headers.get('Authorization', '')
        
        if not auth:
            issues.append("步骤2缺少Authorization header")
        elif '{{' in auth:
            issues.append("步骤2的Authorization是占位符，未被替换")
    
    # 检查步骤2的配置
    if case and len(steps) > 1:
        param_mappings = steps[1].get('param_mappings', [])
        has_token_mapping = any(
            m.get('to_type') == 'headers' and 
            m.get('to_field', '').lower() == 'authorization'
            for m in param_mappings
        )
        
        if not has_token_mapping:
            issues.append("步骤2的param_mappings缺少token映射配置")
    
    if issues:
        print(f"\n❌ 发现 {len(issues)} 个问题:\n")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        
        print(f"\n💡 解决方案:")
        print(f"   运行修复脚本: python fix_scenario_500_error.py")
    else:
        print(f"\n✅ 未发现明显问题")
        print(f"\n如果仍然500错误，可能是:")
        print(f"   1. Token路径不是data.token")
        print(f"   2. 服务器API本身的问题")
        print(f"   3. Token已过期")
    
    conn.close()

if __name__ == "__main__":
    verify_token_extraction()
