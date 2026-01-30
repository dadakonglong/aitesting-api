#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复缺失的必需headers
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def fix_missing_headers():
    print("=" * 80)
    print("🔧 修复缺失的必需headers")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 必需的headers模板
    required_headers = {
        "Content-Type": "application/json",
        "X-Employee-Id": "1PPeP1fdvi",
        "X-Venue-Id": "94YTNnVUk", 
        "X-Mac": "b0:7b:25:16:98:0e"
    }
    
    # 查找所有汇金ERP的测试用例
    c.execute("SELECT id, name, steps FROM test_cases WHERE project_id = '汇金ERP'")
    cases = c.fetchall()
    
    fixed_count = 0
    
    for case in cases:
        case_id = case['id']
        case_name = case['name']
        steps = json.loads(case['steps'])
        
        modified = False
        
        for i, step in enumerate(steps):
            # 跳过第一步（登录接口）
            if i == 0:
                continue
            
            api_path = step.get('api_path', '')
            
            # 只处理业务接口（非登录接口）
            if '/api/v3/' in api_path or '/api/order/' in api_path:
                headers = step.get('headers', {})
                
                # 检查并添加缺失的headers
                for header_name, header_value in required_headers.items():
                    if header_name not in headers:
                        headers[header_name] = header_value
                        modified = True
                        print(f"   ✅ 为用例{case_id}步骤{i+1}添加header: {header_name}")
                
                step['headers'] = headers
        
        if modified:
            # 保存修复后的配置
            c.execute("UPDATE test_cases SET steps = ? WHERE id = ?", 
                     (json.dumps(steps, ensure_ascii=False), case_id))
            fixed_count += 1
            print(f"   💾 已更新测试用例 {case_id}: {case_name}")
    
    conn.commit()
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"✅ 修复完成")
    print("=" * 80)
    print(f"   修复了 {fixed_count} 个测试用例")
    
    if fixed_count > 0:
        print(f"\n💡 添加的headers:")
        for name, value in required_headers.items():
            print(f"   {name}: {value}")
        
        print(f"\n🚀 现在需要:")
        print(f"   1. 重新执行ID58场景")
        print(f"   2. 检查是否包含所有必需的headers")
        print(f"   3. 验证是否能成功执行")
    else:
        print(f"\n   所有测试用例都已包含必需的headers")

def check_headers_coverage():
    """检查headers覆盖情况"""
    print(f"\n" + "=" * 80)
    print(f"📊 检查headers覆盖情况:")
    print("-" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT id, name, steps FROM test_cases WHERE project_id = '汇金ERP' ORDER BY id DESC LIMIT 5")
    cases = c.fetchall()
    
    required_headers = ["Content-Type", "X-Employee-Id", "X-Venue-Id", "X-Mac"]
    
    for case in cases:
        case_id = case['id']
        case_name = case['name']
        steps = json.loads(case['steps'])
        
        print(f"\n用例{case_id}: {case_name}")
        
        for i, step in enumerate(steps[1:], 2):  # 跳过第一步
            api_path = step.get('api_path', '')
            if '/api/v3/' in api_path or '/api/order/' in api_path:
                headers = step.get('headers', {})
                
                print(f"   步骤{i}: {step.get('api_method')} {api_path}")
                
                missing_headers = []
                for header in required_headers:
                    if header in headers:
                        print(f"      ✅ {header}")
                    else:
                        print(f"      ❌ {header} (缺失)")
                        missing_headers.append(header)
                
                if missing_headers:
                    print(f"      ⚠️  缺少 {len(missing_headers)} 个必需header")
    
    conn.close()

if __name__ == "__main__":
    fix_missing_headers()
    check_headers_coverage()