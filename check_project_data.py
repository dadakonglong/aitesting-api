#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查项目数据的一致性
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def check_projects():
    print("=" * 80)
    print("🔍 检查项目数据一致性")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 检查projects表
    print("\n📋 projects表中的项目:")
    c.execute("SELECT * FROM projects")
    projects_in_table = c.fetchall()
    
    if projects_in_table:
        for p in projects_in_table:
            print(f"   - {p['name']} (ID: {p['id']})")
            print(f"     描述: {p['description']}")
            print(f"     创建时间: {p['created_at']}")
    else:
        print("   (空)")
    
    # 2. 检查apis表中的project_id
    print("\n📚 apis表中使用的project_id:")
    c.execute("SELECT DISTINCT project_id FROM apis")
    project_ids_in_apis = [row[0] for row in c.fetchall()]
    
    for pid in project_ids_in_apis:
        c.execute("SELECT COUNT(*) FROM apis WHERE project_id = ?", (pid,))
        count = c.fetchone()[0]
        print(f"   - {pid}: {count}个API")
    
    # 3. 检查scenarios表中的project_id
    print("\n📝 scenarios表中使用的project_id:")
    c.execute("SELECT DISTINCT project_id FROM scenarios")
    project_ids_in_scenarios = [row[0] for row in c.fetchall()]
    
    for pid in project_ids_in_scenarios:
        c.execute("SELECT COUNT(*) FROM scenarios WHERE project_id = ?", (pid,))
        count = c.fetchone()[0]
        print(f"   - {pid}: {count}个场景")
    
    # 4. 检查test_cases表中的project_id
    print("\n📋 test_cases表中使用的project_id:")
    c.execute("SELECT DISTINCT project_id FROM test_cases")
    project_ids_in_cases = [row[0] for row in c.fetchall()]
    
    for pid in project_ids_in_cases:
        c.execute("SELECT COUNT(*) FROM test_cases WHERE project_id = ?", (pid,))
        count = c.fetchone()[0]
        print(f"   - {pid}: {count}个测试用例")
    
    # 5. 找出不一致的数据
    print("\n" + "=" * 80)
    print("🔍 数据一致性分析")
    print("=" * 80)
    
    # 所有在表中使用的project_id
    all_used_ids = set(project_ids_in_apis + project_ids_in_scenarios + project_ids_in_cases)
    
    # projects表中的project_id
    registered_ids = set([p['id'] for p in projects_in_table])
    
    # 找出未注册的project_id
    unregistered_ids = all_used_ids - registered_ids
    
    if unregistered_ids:
        print(f"\n⚠️  发现 {len(unregistered_ids)} 个未在projects表中注册的project_id:")
        for pid in unregistered_ids:
            print(f"\n   项目ID: {pid}")
            
            # 检查这个ID在哪些表中使用
            c.execute("SELECT COUNT(*) FROM apis WHERE project_id = ?", (pid,))
            api_count = c.fetchone()[0]
            if api_count > 0:
                print(f"      - apis表: {api_count}个API")
            
            c.execute("SELECT COUNT(*) FROM scenarios WHERE project_id = ?", (pid,))
            scenario_count = c.fetchone()[0]
            if scenario_count > 0:
                print(f"      - scenarios表: {scenario_count}个场景")
            
            c.execute("SELECT COUNT(*) FROM test_cases WHERE project_id = ?", (pid,))
            case_count = c.fetchone()[0]
            if case_count > 0:
                print(f"      - test_cases表: {case_count}个测试用例")
    else:
        print("\n✅ 所有project_id都已在projects表中注册")
    
    # 6. 建议修复
    if unregistered_ids:
        print("\n" + "=" * 80)
        print("🔧 修复建议")
        print("=" * 80)
        
        print("\n方案1: 将未注册的project_id添加到projects表")
        print("   这样前端就能看到这些项目")
        
        print("\n方案2: 将数据迁移到已注册的项目")
        print("   例如迁移到'55270bf2'项目")
        
        print("\n方案3: 删除未注册项目的数据")
        print("   清理无效数据")
        
        print("\n是否自动修复？(需要手动确认)")
    
    conn.close()

def auto_fix_projects():
    """自动修复：将未注册的project_id添加到projects表"""
    print("\n" + "=" * 80)
    print("🔧 自动修复项目数据")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 获取所有使用的project_id
    c.execute("SELECT DISTINCT project_id FROM apis")
    project_ids = [row[0] for row in c.fetchall()]
    
    # 检查哪些未注册
    fixed_count = 0
    for pid in project_ids:
        c.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (pid,))
        if c.fetchone()[0] == 0:
            # 未注册，添加到projects表
            name = pid if pid != 'default-project' else '默认项目'
            description = f'自动创建的项目（从导入数据中识别）'
            
            c.execute(
                "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
                (pid, name, description)
            )
            print(f"✅ 已添加项目: {name} (ID: {pid})")
            fixed_count += 1
    
    conn.commit()
    conn.close()
    
    if fixed_count > 0:
        print(f"\n✅ 共修复 {fixed_count} 个项目")
        print("   现在前端应该能看到这些项目了")
    else:
        print("\n✅ 无需修复")

if __name__ == "__main__":
    check_projects()
    
    print("\n" + "=" * 80)
    response = input("是否自动修复项目数据？(y/n): ")
    
    if response.lower() == 'y':
        auto_fix_projects()
        print("\n修复完成！请刷新前端页面查看。")
    else:
        print("\n已取消修复")
