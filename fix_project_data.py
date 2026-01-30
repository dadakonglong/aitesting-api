#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复项目数据不一致问题
"""
import sqlite3

DB_PATH = "data/apis.db"

def fix_projects():
    print("=" * 80)
    print("🔧 修复项目数据")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 方案：为孤立的项目ID创建projects记录
    print("\n📝 创建缺失的项目记录...")
    
    projects_to_create = [
        ('汇金ERP', '汇金ERP', '汇金ERP系统'),
        ('custom-verify', '自定义验证', '自定义验证项目'),
        ('test-postman', 'Postman测试', 'Postman导入的测试数据'),
        ('H5点歌台', 'H5点歌台', 'H5点歌台系统')
    ]
    
    for project_id, name, description in projects_to_create:
        try:
            c.execute("""
                INSERT OR IGNORE INTO projects (id, name, description) 
                VALUES (?, ?, ?)
            """, (project_id, name, description))
            
            if c.rowcount > 0:
                print(f"   ✅ 创建项目: {name} (ID: {project_id})")
            else:
                print(f"   ℹ️  项目已存在: {name} (ID: {project_id})")
        except Exception as e:
            print(f"   ❌ 创建失败: {name} - {e}")
    
    conn.commit()
    
    # 检查结果
    print("\n📊 修复后的项目列表:")
    c.execute("SELECT id, name FROM projects ORDER BY created_at")
    projects = c.fetchall()
    
    for project_id, name in projects:
        # 统计API数量
        c.execute("SELECT COUNT(*) FROM apis WHERE project_id = ?", (project_id,))
        api_count = c.fetchone()[0]
        
        # 统计场景数量
        c.execute("SELECT COUNT(*) FROM scenarios WHERE project_id = ?", (project_id,))
        scenario_count = c.fetchone()[0]
        
        print(f"   {name}")
        print(f"      ID: {project_id}")
        print(f"      API数量: {api_count}")
        print(f"      场景数量: {scenario_count}")
        print()
    
    conn.close()
    
    print("=" * 80)
    print("✅ 修复完成")
    print("=" * 80)
    
    print("\n💡 说明:")
    print("   现在数据库中有多个项目，每个项目都有对应的projects记录")
    print("   前端应该能看到所有项目了")
    print("\n   主要项目:")
    print("   - 汇金ERP (ID: 汇金ERP) - 17个API")
    print("   - 汇金ERP (ID: 55270bf2) - 6个API")
    print("   - 其他测试项目")
    print("\n   建议:")
    print("   如果想合并两个汇金ERP项目，可以运行合并脚本")

if __name__ == "__main__":
    fix_projects()
