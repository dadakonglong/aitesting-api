#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查最新生成的场景配置
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def check_latest_scenario():
    print("=" * 80)
    print("🔍 检查最新生成的场景")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取最新的场景
    c.execute("""
        SELECT s.*, t.steps 
        FROM scenarios s 
        LEFT JOIN test_cases t ON s.test_case_id = t.id 
        WHERE s.project_id = '汇金ERP'
        ORDER BY s.id DESC 
        LIMIT 1
    """)
    
    scenario = c.fetchone()
    
    if not scenario:
        print("❌ 没有找到场景")
        conn.close()
        return
    
    print(f"\n📝 场景信息:")
    print(f"   ID: {scenario['id']}")
    print(f"   名称: {scenario['name']}")
    print(f"   描述: {scenario['natural_language_input']}")
    print(f"   测试用例ID: {scenario['test_case_id']}")
    
    if not scenario['steps']:
        print("\n⚠️  场景还没有生成测试用例")
        conn.close()
        return
    
    steps = json.loads(scenario['steps'])
    
    print(f"\n📋 测试步骤 ({len(steps)}个):")
    print("=" * 80)
    
    for i, step in enumerate(steps, 1):
        print(f"\n步骤{i}: {step.get('api_method')} {step.get('api_path')}")
        print(f"   描述: {step.get('description', 'N/A')}")
        
        # 检查参数映射
        param_mappings = step.get('param_mappings', [])
        print(f"\n   参数映射 ({len(param_mappings)}个):")
        
        if param_mappings:
            for mapping in param_mappings:
                from_step = mapping.get('from_step')
                from_field = mapping.get('from_field')
                to_field = mapping.get('to_field')
                to_type = mapping.get('to_type', 'params')
                
                print(f"      ✓ 从步骤{from_step}的{from_field} -> {to_type}.{to_field}")
                
                # 检查是否有问题
                if from_step == i:
                    print(f"         ❌ 错误：自引用！步骤{i}不能引用自己")
                elif from_step > i:
                    print(f"         ❌ 错误：引用未来步骤！步骤{i}不能引用步骤{from_step}")
        else:
            if i == 1:
                print(f"      ✓ 无映射（第一步通常不需要）")
            else:
                # 检查是否需要token
                headers = step.get('headers', {})
                needs_auth = any('authorization' in k.lower() or 'token' in str(v).lower() 
                               for k, v in headers.items())
                
                if needs_auth:
                    print(f"      ⚠️  警告：此步骤可能需要token，但没有配置映射")
                else:
                    print(f"      - 无映射")
        
        # 检查请求头
        headers = step.get('headers', {})
        if headers:
            print(f"\n   请求头:")
            for key, value in headers.items():
                if '{{' in str(value):
                    print(f"      ⚠️  {key}: {value} (占位符，未配置映射)")
                else:
                    print(f"      ✓ {key}: {value}")
        
        # 检查请求参数
        params = step.get('params', {})
        if params:
            print(f"\n   请求参数 (前5个):")
            for key, value in list(params.items())[:5]:
                if '{{' in str(value):
                    print(f"      ⚠️  {key}: {value} (占位符，未配置映射)")
                else:
                    print(f"      ✓ {key}: {value}")
    
    # 总结问题
    print("\n" + "=" * 80)
    print("🔍 问题诊断:")
    print("=" * 80)
    
    issues = []
    
    for i, step in enumerate(steps, 1):
        param_mappings = step.get('param_mappings', [])
        
        # 检查自引用
        for mapping in param_mappings:
            if mapping.get('from_step') == i:
                issues.append(f"步骤{i}有自引用错误")
        
        # 检查是否缺少token映射
        if i > 1:
            headers = step.get('headers', {})
            needs_auth = any('authorization' in k.lower() or 'token' in str(v).lower() 
                           for k, v in headers.items())
            
            has_auth_mapping = any(
                m.get('to_type') == 'headers' and 
                m.get('to_field', '').lower() == 'authorization'
                for m in param_mappings
            )
            
            if needs_auth and not has_auth_mapping:
                issues.append(f"步骤{i}需要token但缺少映射")
    
    if issues:
        print(f"\n   发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"      ❌ {issue}")
        
        print(f"\n💡 解决方案:")
        print(f"   运行修复脚本: python fix_scenario_500_error.py")
    else:
        print(f"\n   ✅ 配置看起来正确")
        print(f"\n   如果仍然失败，可能是:")
        print(f"      1. Token路径不对（不是data.token）")
        print(f"      2. 业务逻辑问题（如门店权限）")
        print(f"      3. 其他必需参数缺失")
    
    conn.close()

if __name__ == "__main__":
    check_latest_scenario()
