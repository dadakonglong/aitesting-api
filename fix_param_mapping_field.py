#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复param_mappings的to_field配置错误
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def fix_param_mapping():
    print("=" * 80)
    print("🔧 修复param_mappings配置")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 查找所有有问题的param_mappings
    c.execute("SELECT id, name, steps FROM test_cases WHERE project_id = '汇金ERP'")
    cases = c.fetchall()
    
    fixed_count = 0
    
    for case in cases:
        case_id = case['id']
        steps = json.loads(case['steps'])
        
        modified = False
        
        for step in steps:
            param_mappings = step.get('param_mappings', [])
            
            for mapping in param_mappings:
                # 检查错误的to_field配置
                to_field = mapping.get('to_field')
                
                if to_field == 'headers.Authorization':
                    print(f"   ❌ 发现错误配置: to_field = 'headers.Authorization'")
                    print(f"      应该是: to_field = 'Authorization', to_type = 'headers'")
                    
                    # 修复配置
                    mapping['to_field'] = 'Authorization'
                    mapping['to_type'] = 'headers'
                    modified = True
                    
                    print(f"   ✅ 已修复为: to_field = 'Authorization', to_type = 'headers'")
        
        if modified:
            # 保存修复后的配置
            c.execute("UPDATE test_cases SET steps = ? WHERE id = ?", 
                     (json.dumps(steps, ensure_ascii=False), case_id))
            fixed_count += 1
            print(f"   💾 已更新测试用例 {case_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n" + "=" * 80)
    print(f"✅ 修复完成")
    print("=" * 80)
    print(f"   修复了 {fixed_count} 个测试用例")
    
    if fixed_count > 0:
        print(f"\n💡 现在需要:")
        print(f"   1. 重新执行场景")
        print(f"   2. 检查token是否正确提取")
        print(f"   3. 查看调试日志确认修复效果")
    else:
        print(f"\n   没有发现需要修复的配置")

if __name__ == "__main__":
    fix_param_mapping()