#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查ID58的问题
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def check_id58():
    print("=" * 80)
    print("🔍 检查ID58的问题")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 查找ID58
    print("\n📋 查找ID58:")
    
    # 检查场景58
    c.execute("SELECT * FROM scenarios WHERE id = 58")
    scenario58 = c.fetchone()
    
    if scenario58:
        print(f"   ✅ 找到场景58: {scenario58['name']}")
        print(f"   测试用例ID: {scenario58['test_case_id']}")
        test_case_id = scenario58['test_case_id']
    else:
        # 检查测试用例58
        c.execute("SELECT * FROM test_cases WHERE id = 58")
        case58 = c.fetchone()
        
        if case58:
            print(f"   ✅ 找到测试用例58: {case58['name']}")
            test_case_id = 58
        else:
            print("   ❌ 找不到ID58")
            
            # 显示最新的场景和用例
            print("\n   最新的场景:")
            c.execute("SELECT id, name FROM scenarios ORDER BY id DESC LIMIT 5")
            for s in c.fetchall():
                print(f"      场景{s['id']}: {s['name']}")
            
            print("\n   最新的测试用例:")
            c.execute("SELECT id, name FROM test_cases ORDER BY id DESC LIMIT 5")
            for case in c.fetchall():
                print(f"      用例{case['id']}: {case['name']}")
            
            conn.close()
            return
    
    # 2. 检查测试用例配置
    c.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,))
    case = c.fetchone()
    
    if not case:
        print(f"   ❌ 找不到测试用例{test_case_id}")
        conn.close()
        return
    
    steps = json.loads(case['steps'])
    
    print(f"\n📝 ID58的配置:")
    print(f"   名称: {case['name']}")
    print(f"   步骤数: {len(steps)}")
    
    # 检查前3步的param_mappings
    for i in range(min(3, len(steps))):
        step = steps[i]
        print(f"\n   步骤{i+1}: {step.get('api_method')} {step.get('api_path')}")
        
        param_mappings = step.get('param_mappings', [])
        print(f"   param_mappings ({len(param_mappings)}个):")
        
        if param_mappings:
            for mapping in param_mappings:
                from_step = mapping.get('from_step')
                from_field = mapping.get('from_field')
                to_field = mapping.get('to_field')
                to_type = mapping.get('to_type', 'params')
                
                print(f"      从步骤{from_step}的{from_field} -> {to_type}.{to_field}")
                
                # 检查配置是否正确
                if to_type == 'headers' and to_field == 'Authorization':
                    print(f"         ✅ token映射配置正确")
                elif 'headers.Authorization' in to_field:
                    print(f"         ❌ 错误配置：to_field包含'headers.'")
                elif to_field == 'Authorization' and to_type != 'headers':
                    print(f"         ❌ 错误配置：to_type应该是'headers'")
        else:
            if i == 0:
                print(f"      ✅ 第一步无映射（正常）")
            else:
                print(f"      ⚠️  可能缺少token映射")
    
    # 3. 检查最近的执行记录
    print(f"\n" + "=" * 80)
    print(f"📊 ID58的最近执行:")
    print("-" * 80)
    
    c.execute("""
        SELECT * FROM executions 
        WHERE test_case_id = ? 
        ORDER BY id DESC 
        LIMIT 2
    """, (test_case_id,))
    
    executions = c.fetchall()
    
    if executions:
        for exec_rec in executions:
            print(f"\n执行{exec_rec['id']} ({exec_rec['created_at']}):")
            print(f"   状态: {exec_rec['status']}")
            
            results = json.loads(exec_rec['results'])
            
            for j, result in enumerate(results[:3], 1):
                print(f"\n   步骤{j}: {result.get('method')} {result.get('url')}")
                print(f"      状态码: {result.get('status_code')}")
                print(f"      成功: {result.get('success')}")
                
                # 检查提取记录
                extractions = result.get('extractions', [])
                if extractions:
                    print(f"      提取记录 ({len(extractions)}个):")
                    for ext in extractions:
                        success = ext.get('success', False)
                        status_icon = "✅" if success else "❌"
                        print(f"         {status_icon} 从步骤{ext.get('from_step')}提取{ext.get('from_field')}")
                        
                        if success:
                            value = str(ext.get('extracted_value', ''))[:30]
                            print(f"            提取值: {value}...")
                        else:
                            print(f"            错误: {ext.get('error_msg')}")
                
                # 检查Authorization header
                req_headers = result.get('request_headers', {})
                auth = req_headers.get('Authorization', '')
                
                if auth:
                    if 'Bearer' in auth and len(auth) > 20:
                        print(f"      Authorization: {auth[:50]}...")
                    else:
                        print(f"      Authorization异常: {auth}")
                else:
                    if j > 1:  # 第2步及以后应该有Authorization
                        print(f"      ❌ 缺少Authorization header")
                
                # 检查响应
                response = result.get('response', {})
                if isinstance(response, dict):
                    code = response.get('code')
                    message = response.get('message')
                    print(f"      响应: code={code}, message={message}")
    else:
        print(f"   ❌ 没有找到ID58的执行记录")
    
    # 4. 对比ID37和ID58的差异
    print(f"\n" + "=" * 80)
    print(f"🔍 对比ID37（成功）和ID58（失败）:")
    print("-" * 80)
    
    # 获取ID37的配置
    c.execute("SELECT * FROM scenarios WHERE id = 37")
    scenario37 = c.fetchone()
    
    if scenario37:
        c.execute("SELECT * FROM test_cases WHERE id = ?", (scenario37['test_case_id'],))
        case37 = c.fetchone()
        
        if case37:
            steps37 = json.loads(case37['steps'])
            
            print(f"\n   ID37步骤数: {len(steps37)}")
            print(f"   ID58步骤数: {len(steps)}")
            
            # 对比步骤2的配置
            if len(steps37) >= 2 and len(steps) >= 2:
                step2_37 = steps37[1]
                step2_58 = steps[1]
                
                print(f"\n   步骤2对比:")
                print(f"   ID37: {step2_37.get('api_method')} {step2_37.get('api_path')}")
                print(f"   ID58: {step2_58.get('api_method')} {step2_58.get('api_path')}")
                
                mappings37 = step2_37.get('param_mappings', [])
                mappings58 = step2_58.get('param_mappings', [])
                
                print(f"\n   param_mappings对比:")
                print(f"   ID37: {len(mappings37)}个映射")
                for m in mappings37:
                    print(f"      {m.get('from_field')} -> {m.get('to_type', 'params')}.{m.get('to_field')}")
                
                print(f"   ID58: {len(mappings58)}个映射")
                for m in mappings58:
                    print(f"      {m.get('from_field')} -> {m.get('to_type', 'params')}.{m.get('to_field')}")
    
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"💡 诊断建议:")
    print("=" * 80)
    print("""
1. 检查ID58的param_mappings配置是否正确
2. 检查提取记录是否显示成功
3. 检查Authorization header是否正确设置
4. 对比ID37和ID58的配置差异
5. 如果配置正确但仍失败，可能是业务逻辑问题
    """)

if __name__ == "__main__":
    check_id58()