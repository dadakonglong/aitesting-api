#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的所有项目和API数据
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def check_all_projects():
    print("=" * 80)
    print("🔍 检查数据库中的所有项目")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. 检查projects表
    print("\n📋 Projects表:")
    try:
        c.execute("SELECT * FROM projects ORDER BY created_at DESC")
        projects = c.fetchall()
        
        if projects:
            print(f"   找到 {len(projects)} 个项目:\n")
            for p in projects:
                print(f"   ID: {p['id']}")
                print(f"   名称: {p['name']}")
                print(f"   描述: {p['description'] or '(无)'}")
                print(f"   创建时间: {p['created_at']}")
                print()
        else:
            print("   ⚠️  Projects表为空")
    except Exception as e:
        print(f"   ❌ 读取Projects表失败: {e}")
    
    # 2. 检查APIs表中的project_id
    print("\n" + "=" * 80)
    print("📚 APIs表中的项目分布:")
    print("=" * 80)
    
    c.execute("""
        SELECT project_id, COUNT(*) as api_count 
        FROM apis 
        GROUP BY project_id 
        ORDER BY api_count DESC
    """)
    api_projects = c.fetchall()
    
    if api_projects:
        print(f"\n   找到 {len(api_projects)} 个项目有API数据:\n")
        for ap in api_projects:
            project_id = ap['project_id']
            api_count = ap['api_count']
            
            print(f"   项目ID: {project_id}")
            print(f"   API数量: {api_count}")
            
            # 检查这个project_id是否在projects表中
            c.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project = c.fetchone()
            if project:
                print(f"   项目名称: {project['name']}")
            else:
                print(f"   ⚠️  此项目ID不在projects表中")
            
            # 显示前5个API
            c.execute("""
                SELECT path, method, summary 
                FROM apis 
                WHERE project_id = ? 
                LIMIT 5
            """, (project_id,))
            apis = c.fetchall()
            
            print(f"   前5个API:")
            for api in apis:
                print(f"      {api['method']:6s} {api['path']}")
            print()
    else:
        print("   ⚠️  APIs表为空")
    
    # 3. 检查场景表
    print("=" * 80)
    print("📝 Scenarios表中的项目分布:")
    print("=" * 80)
    
    c.execute("""
        SELECT project_id, COUNT(*) as scenario_count 
        FROM scenarios 
        GROUP BY project_id 
        ORDER BY scenario_count DESC
    """)
    scenario_projects = c.fetchall()
    
    if scenario_projects:
        print(f"\n   找到 {len(scenario_projects)} 个项目有场景数据:\n")
        for sp in scenario_projects:
            project_id = sp['project_id']
            scenario_count = sp['scenario_count']
            
            print(f"   项目ID: {project_id}")
            print(f"   场景数量: {scenario_count}")
            
            # 检查这个project_id是否在projects表中
            c.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project = c.fetchone()
            if project:
                print(f"   项目名称: {project['name']}")
            else:
                print(f"   ⚠️  此项目ID不在projects表中")
            print()
    else:
        print("   ⚠️  Scenarios表为空")
    
    # 4. 数据一致性检查
    print("=" * 80)
    print("🔍 数据一致性检查:")
    print("=" * 80)
    
    issues = []
    
    # 检查APIs表中的project_id是否都在projects表中
    c.execute("SELECT DISTINCT project_id FROM apis")
    api_project_ids = [row[0] for row in c.fetchall()]
    
    c.execute("SELECT id FROM projects")
    project_ids = [row[0] for row in c.fetchall()]
    
    orphan_api_projects = set(api_project_ids) - set(project_ids)
    if orphan_api_projects:
        issues.append(f"APIs表中有 {len(orphan_api_projects)} 个项目ID不在projects表中: {orphan_api_projects}")
    
    # 检查scenarios表中的project_id是否都在projects表中
    c.execute("SELECT DISTINCT project_id FROM scenarios")
    scenario_project_ids = [row[0] for row in c.fetchall()]
    
    orphan_scenario_projects = set(scenario_project_ids) - set(project_ids)
    if orphan_scenario_projects:
        issues.append(f"Scenarios表中有 {len(orphan_scenario_projects)} 个项目ID不在projects表中: {orphan_scenario_projects}")
    
    if issues:
        print(f"\n   发现 {len(issues)} 个问题:\n")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        
        print("\n💡 建议:")
        print("   这些孤立的项目ID需要在projects表中创建对应的记录")
        print("   或者将它们的数据迁移到已存在的项目中")
    else:
        print("\n   ✅ 数据一致性良好")
    
    # 5. 修复建议
    if orphan_api_projects or orphan_scenario_projects:
        print("\n" + "=" * 80)
        print("🔧 修复方案:")
        print("=" * 80)
        
        all_orphans = orphan_api_projects | orphan_scenario_projects
        
        print("\n   方案1: 为孤立的项目ID创建projects记录")
        print("   " + "-" * 76)
        for project_id in all_orphans:
            # 尝试从API数据推断项目名称
            c.execute("SELECT base_url FROM apis WHERE project_id = ? LIMIT 1", (project_id,))
            row = c.fetchone()
            base_url = row[0] if row and row[0] else ""
            
            suggested_name = project_id
            if "汇金" in base_url or "huijin" in base_url.lower():
                suggested_name = "汇金ERP"
            elif "erp" in base_url.lower():
                suggested_name = f"ERP系统-{project_id[:8]}"
            
            print(f"   INSERT INTO projects (id, name, description) VALUES")
            print(f"   ('{project_id}', '{suggested_name}', '自动创建');")
        
        print("\n   方案2: 将数据迁移到default-project")
        print("   " + "-" * 76)
        for project_id in all_orphans:
            print(f"   UPDATE apis SET project_id = 'default-project' WHERE project_id = '{project_id}';")
            print(f"   UPDATE scenarios SET project_id = 'default-project' WHERE project_id = '{project_id}';")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 检查完成")
    print("=" * 80)

if __name__ == "__main__":
    check_all_projects()
