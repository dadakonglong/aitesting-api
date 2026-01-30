#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比能工作的场景和不能工作的场景
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def compare_scenarios():
    print("=" * 80)
    print("🔍 对比场景配置")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取用例37（能工作的）
    print("\n📋 用例37 (能工作的):")
    print("-" * 80)
    
    c.execute("SELECT * FROM test_cases WHERE id = 37")
    case37 = c.fetchone()
    
    if case37:
        steps37 = json.loads(case37['steps'])
        print(f"   名称: {case37['name']}")
        print(f"   步骤数: {len(steps37)}")
        
        # 显示前2步的配置
        for i in range(min(2, len(steps37))):
            step = steps37[i]
            print(f"\n   步骤{i+1}: {step.get('api_method')} {step.get('api_path')}")
            
            param_mappings = step.get('param_mappings', [])
            print(f"   param_mappings:")
            if param_mappings:
                for m in param_mappings:
                    print(f"      {json.dumps(m, ensure_ascii=False)}")
            else:
                print(f"      []")
            
            headers = step.get('headers', {})
            if headers:
                print(f"   headers:")
                for k, v in headers.items():
                    print(f"      {k}: {v}")
    else:
        print("   ❌ 找不到用例37")
    
    # 获取最新的用例
    print("\n" + "=" * 80)
    print("📋 最新用例 (不能工作的):")
    print("-" * 80)
    
    c.execute("""
        SELECT * FROM test_cases 
        WHERE project_id = '汇金ERP'
        ORDER BY id DESC 
        LIMIT 1
    """)
    latest_case = c.fetchone()
    
    if latest_case:
        latest_steps = json.loads(latest_case['steps'])
        print(f"   ID: {latest_case['id']}")
        print(f"   名称: {latest_case['name']}")
        print(f"   步骤数: {len(latest_steps)}")
        
        # 显示前2步的配置
        for i in range(min(2, len(latest_steps))):
            step = latest_steps[i]
            print(f"\n   步骤{i+1}: {step.get('api_method')} {step.get('api_path')}")
            
            param_mappings = step.get('param_mappings', [])
            print(f"   param_mappings:")
            if param_mappings:
                for m in param_mappings:
                    print(f"      {json.dumps(m, ensure_ascii=False)}")
            else:
                print(f"      []")
            
            headers = step.get('headers', {})
            if headers:
                print(f"   headers:")
                for k, v in headers.items():
                    print(f"      {k}: {v}")
    else:
        print("   ❌ 找不到最新用例")
    
    # 对比差异
    print("\n" + "=" * 80)
    print("🔍 关键差异:")
    print("=" * 80)
    
    if case37 and latest_case:
        steps37 = json.loads(case37['steps'])
        latest_steps = json.loads(latest_case['steps'])
        
        # 对比步骤2的param_mappings
        if len(steps37) >= 2 and len(latest_steps) >= 2:
            step2_37 = steps37[1]
            step2_latest = latest_steps[1]
            
            mappings_37 = step2_37.get('param_mappings', [])
            mappings_latest = step2_latest.get('param_mappings', [])
            
            print(f"\n步骤2的param_mappings对比:")
            print(f"\n   用例37:")
            for m in mappings_37:
                print(f"      {json.dumps(m, ensure_ascii=False, indent=8)}")
            
            print(f"\n   最新用例:")
            for m in mappings_latest:
                print(f"      {json.dumps(m, ensure_ascii=False, indent=8)}")
            
            # 检查差异
            print(f"\n   差异分析:")
            
            # 检查token映射
            has_token_37 = any(
                m.get('to_type') == 'headers' and 
                m.get('to_field') == 'Authorization'
                for m in mappings_37
            )
            
            has_token_latest = any(
                m.get('to_type') == 'headers' and 
                m.get('to_field') == 'Authorization'
                for m in mappings_latest
            )
            
            if has_token_37 and has_token_latest:
                print(f"      ✅ 两者都有token映射")
                
                # 检查from_field
                token_37 = next((m for m in mappings_37 
                               if m.get('to_type') == 'headers' and 
                               m.get('to_field') == 'Authorization'), None)
                
                token_latest = next((m for m in mappings_latest 
                                   if m.get('to_type') == 'headers' and 
                                   m.get('to_field') == 'Authorization'), None)
                
                if token_37 and token_latest:
                    if token_37.get('from_field') != token_latest.get('from_field'):
                        print(f"      ⚠️  from_field不同:")
                        print(f"         用例37: {token_37.get('from_field')}")
                        print(f"         最新: {token_latest.get('from_field')}")
                    else:
                        print(f"      ✅ from_field相同: {token_37.get('from_field')}")
            elif has_token_37 and not has_token_latest:
                print(f"      ❌ 最新用例缺少token映射")
            elif not has_token_37 and has_token_latest:
                print(f"      ⚠️  用例37没有token映射，但最新用例有")
    
    # 检查最近的执行记录
    print("\n" + "=" * 80)
    print("📊 最近的执行记录:")
    print("=" * 80)
    
    c.execute("""
        SELECT id, test_case_id, status, results 
        FROM executions 
        ORDER BY id DESC 
        LIMIT 3
    """)
    
    executions = c.fetchall()
    
    for exec_rec in executions:
        print(f"\n执行 {exec_rec['id']} (用例 {exec_rec['test_case_id']}):")
        
        results = json.loads(exec_rec['results'])
        
        if len(results) >= 2:
            step1 = results[0]
            step2 = results[1]
            
            print(f"   步骤1: {step1.get('status_code')} - {step1.get('success')}")
            
            # 检查步骤1的响应中是否有token
            response1 = step1.get('response', {})
            if isinstance(response1, dict):
                token = response1.get('data', {}).get('token')
                if token:
                    print(f"      ✅ 返回了token: {str(token)[:30]}...")
                else:
                    print(f"      ❌ 没有返回token")
            
            print(f"   步骤2: {step2.get('status_code')} - {step2.get('success')}")
            
            # 检查步骤2的请求头
            headers2 = step2.get('request_headers', {})
            auth = headers2.get('Authorization', '')
            
            if auth:
                if 'Bearer' in auth and len(auth) > 20:
                    print(f"      ✅ Authorization: {auth[:50]}...")
                else:
                    print(f"      ⚠️  Authorization格式异常: {auth}")
            else:
                print(f"      ❌ 缺少Authorization header")
            
            # 检查步骤2的响应
            response2 = step2.get('response', {})
            if isinstance(response2, dict):
                code = response2.get('code')
                message = response2.get('message')
                print(f"      响应: code={code}, message={message}")
    
    conn.close()

if __name__ == "__main__":
    compare_scenarios()
