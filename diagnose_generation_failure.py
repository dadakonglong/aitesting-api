#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断场景生成失败的原因
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def diagnose():
    print("=" * 80)
    print("🔍 诊断场景生成失败")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 检查项目
    print("\n📋 项目信息:")
    c.execute("SELECT DISTINCT project_id FROM apis")
    projects = [row[0] for row in c.fetchall()]
    print(f"   可用项目: {projects}")
    
    # 2. 检查汇金ERP项目的API
    print("\n📚 汇金ERP项目的API:")
    c.execute("SELECT COUNT(*) FROM apis WHERE project_id = '汇金ERP'")
    count = c.fetchone()[0]
    print(f"   API数量: {count}")
    
    if count > 0:
        c.execute("""
            SELECT path, method, summary 
            FROM apis 
            WHERE project_id = '汇金ERP' 
            LIMIT 10
        """)
        apis = c.fetchall()
        print(f"\n   前10个API:")
        for api in apis:
            print(f"      {api['method']:6s} {api['path']}")
    
    # 3. 检查最近的场景
    print("\n📝 最近的场景:")
    c.execute("""
        SELECT id, name, project_id, test_case_id, created_at 
        FROM scenarios 
        WHERE project_id = '汇金ERP'
        ORDER BY id DESC 
        LIMIT 5
    """)
    scenarios = c.fetchall()
    
    if scenarios:
        for s in scenarios:
            status = "✅ 已生成用例" if s['test_case_id'] else "⏳ 未生成用例"
            print(f"   场景{s['id']}: {s['name']} - {status}")
    else:
        print(f"   (无场景)")
    
    # 4. 检查最近的测试用例
    print("\n📋 最近的测试用例:")
    c.execute("""
        SELECT id, name, project_id, created_at 
        FROM test_cases 
        WHERE project_id = '汇金ERP'
        ORDER BY id DESC 
        LIMIT 5
    """)
    cases = c.fetchall()
    
    if cases:
        for case in cases:
            print(f"   用例{case['id']}: {case['name']}")
    else:
        print(f"   (无测试用例)")
    
    # 5. 检查环境变量
    print("\n🔧 环境配置:")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    provider = os.getenv("AI_PROVIDER", "openai")
    
    print(f"   AI_PROVIDER: {provider}")
    print(f"   OPENAI_API_KEY: {'✅ 已配置' if openai_key else '❌ 未配置'}")
    print(f"   DEEPSEEK_API_KEY: {'✅ 已配置' if deepseek_key else '❌ 未配置'}")
    
    if provider == "openai" and not openai_key:
        print(f"\n   ⚠️  警告: AI_PROVIDER设置为openai，但OPENAI_API_KEY未配置")
    elif provider == "deepseek" and not deepseek_key:
        print(f"\n   ⚠️  警告: AI_PROVIDER设置为deepseek，但DEEPSEEK_API_KEY未配置")
    
    # 6. 常见问题检查
    print("\n💡 常见问题检查:")
    
    issues = []
    
    if count == 0:
        issues.append("汇金ERP项目中没有API数据")
    
    if not openai_key and not deepseek_key:
        issues.append("未配置任何AI服务的API Key")
    
    if issues:
        print(f"   发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print(f"   ✅ 未发现明显问题")
    
    conn.close()
    
    # 7. 建议
    print("\n🔧 排查建议:")
    print("   1. 检查浏览器控制台的错误信息")
    print("   2. 检查后端服务日志（如果使用Docker）")
    print("   3. 尝试重新启动AI服务")
    print("   4. 检查网络连接（AI服务需要访问外网）")
    print("   5. 尝试使用更简单的测试意图，如'测试登录'")

if __name__ == "__main__":
    diagnose()
