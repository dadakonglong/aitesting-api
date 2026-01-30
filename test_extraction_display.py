#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试提取记录显示
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def test_extraction_display():
    print("=" * 80)
    print("🔍 测试提取记录显示")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取最近的执行记录
    c.execute("""
        SELECT id, test_case_id, results 
        FROM executions 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    execution = c.fetchone()
    
    if not execution:
        print("❌ 没有找到执行记录")
        print("   请先执行一个场景")
        conn.close()
        return
    
    print(f"\n📊 执行记录 ID: {execution['id']}")
    print(f"   测试用例 ID: {execution['test_case_id']}")
    
    results = json.loads(execution['results'])
    
    print(f"\n📋 步骤执行结果:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n步骤{i}: {result.get('method')} {result.get('url')}")
        print(f"   状态: {result.get('status_code')} - {'✅ 成功' if result.get('success') else '❌ 失败'}")
        
        # 显示提取记录
        extractions = result.get('extractions', [])
        
        if extractions:
            print(f"\n   📦 参数提取 ({len(extractions)}个):")
            print("   " + "-" * 76)
            
            for extraction in extractions:
                from_step = extraction.get('from_step')
                from_field = extraction.get('from_field')
                to_field = extraction.get('to_field')
                to_type = extraction.get('to_type', 'params')
                success = extraction.get('success', False)
                extracted_value = extraction.get('extracted_value')
                error_msg = extraction.get('error_msg')
                
                status_icon = "✅" if success else "❌"
                
                print(f"\n   {status_icon} 从步骤{from_step}提取")
                print(f"      来源字段: {from_field}")
                print(f"      目标位置: {to_type}.{to_field}")
                
                if success:
                    # 显示提取的值（截断长值）
                    value_str = str(extracted_value)
                    if len(value_str) > 60:
                        value_str = value_str[:60] + "..."
                    print(f"      提取的值: {value_str}")
                else:
                    print(f"      错误: {error_msg}")
        else:
            if i > 1:
                print(f"\n   ⚠️  此步骤没有参数提取记录")
                print(f"      可能原因:")
                print(f"      1. 没有配置param_mappings")
                print(f"      2. 或使用的是旧版本的执行引擎")
            else:
                print(f"\n   ℹ️  第一步通常不需要提取参数")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("💡 说明:")
    print("=" * 80)
    print("""
前端的"提取"标签页会显示这些提取记录，包括：
- 从哪个步骤提取
- 提取哪个字段
- 提取到的值
- 设置到哪里

这样你就能清楚地看到token是否被正确提取和传递。

如果看不到提取记录，请：
1. 重启AI服务（使用更新后的代码）
2. 重新执行场景
3. 刷新前端页面
    """)

if __name__ == "__main__":
    test_extraction_display()
