#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并两个汇金ERP项目
"""
import sqlite3

DB_PATH = "data/apis.db"

def merge_projects():
    print("=" * 80)
    print("🔀 合并汇金ERP项目")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 目标项目ID（保留这个）
    target_id = "汇金ERP"
    # 源项目ID（合并到目标）
    source_id = "55270bf2"
    
    print(f"\n📋 合并方案:")
    print(f"   源项目: {source_id} (6个API, 4个场景)")
    print(f"   目标项目: {target_id} (17个API, 8个场景)")
    print(f"   操作: 将源项目的数据迁移到目标项目")
    
    # 1. 检查是否有重复的API
    print(f"\n🔍 检查重复API...")
    c.execute("""
        SELECT a1.path, a1.method 
        FROM apis a1 
        WHERE a1.project_id = ? 
        AND EXISTS (
            SELECT 1 FROM apis a2 
            WHERE a2.project_id = ? 
            AND a2.path = a1.path 
            AND a2.method = a1.method
        )
    """, (source_id, target_id))
    
    duplicates = c.fetchall()
    if duplicates:
        print(f"   ⚠️  发现 {len(duplicates)} 个重复API:")
        for path, method in duplicates[:5]:
            print(f"      {method} {path}")
        if len(duplicates) > 5:
            print(f"      ... 还有 {len(duplicates) - 5} 个")
    else:
        print(f"   ✅ 没有重复API")
    
    # 2. 迁移API数据
    print(f"\n📦 迁移API数据...")
    c.execute("""
        UPDATE apis 
        SET project_id = ? 
        WHERE project_id = ?
    """, (target_id, source_id))
    
    api_migrated = c.rowcount
    print(f"   ✅ 迁移了 {api_migrated} 个API")
    
    # 3. 迁移场景数据
    print(f"\n📝 迁移场景数据...")
    c.execute("""
        UPDATE scenarios 
        SET project_id = ? 
        WHERE project_id = ?
    """, (target_id, source_id))
    
    scenario_migrated = c.rowcount
    print(f"   ✅ 迁移了 {scenario_migrated} 个场景")
    
    # 4. 迁移测试用例数据
    print(f"\n📋 迁移测试用例数据...")
    c.execute("""
        UPDATE test_cases 
        SET project_id = ? 
        WHERE project_id = ?
    """, (target_id, source_id))
    
    case_migrated = c.rowcount
    print(f"   ✅ 迁移了 {case_migrated} 个测试用例")
    
    # 5. 删除源项目记录
    print(f"\n🗑️  删除源项目记录...")
    c.execute("DELETE FROM projects WHERE id = ?", (source_id,))
    print(f"   ✅ 已删除项目: {source_id}")
    
    conn.commit()
    
    # 6. 验证结果
    print(f"\n📊 合并后的汇金ERP项目:")
    c.execute("SELECT COUNT(*) FROM apis WHERE project_id = ?", (target_id,))
    api_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM scenarios WHERE project_id = ?", (target_id,))
    scenario_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM test_cases WHERE project_id = ?", (target_id,))
    case_count = c.fetchone()[0]
    
    print(f"   API数量: {api_count}")
    print(f"   场景数量: {scenario_count}")
    print(f"   测试用例数量: {case_count}")
    
    # 7. 显示API列表
    print(f"\n📚 API列表 (前10个):")
    c.execute("""
        SELECT path, method, summary 
        FROM apis 
        WHERE project_id = ? 
        ORDER BY path 
        LIMIT 10
    """, (target_id,))
    
    apis = c.fetchall()
    for path, method, summary in apis:
        print(f"   {method:6s} {path}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 合并完成")
    print("=" * 80)
    
    print("\n💡 说明:")
    print("   现在只有一个汇金ERP项目 (ID: 汇金ERP)")
    print("   包含所有的API和场景数据")
    print("   前端刷新后应该能看到完整的数据")

if __name__ == "__main__":
    # 确认操作
    print("⚠️  警告: 此操作将合并两个汇金ERP项目")
    print("   源项目 (55270bf2) 将被删除")
    print("   所有数据将迁移到目标项目 (汇金ERP)")
    
    confirm = input("\n是否继续? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        merge_projects()
    else:
        print("\n❌ 操作已取消")
