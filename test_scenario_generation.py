#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完整的场景生成流程
"""
import asyncio
import sys
import sqlite3
import json

sys.path.insert(0, 'services/ai-processing')

from main_sqlite import ai_client, DB_PATH

async def test_scenario_generation():
    print("=" * 80)
    print("🧪 测试场景生成流程")
    print("=" * 80)
    
    # 1. 创建测试场景
    print("\n步骤1: 创建测试场景")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    test_input = "测试用户登录后查询订单"
    
    # 模拟NLU结果
    nlu_result = {
        "intent": "测试登录和查询订单",
        "entities": ["用户", "订单"],
        "actions": ["登录", "查询"]
    }
    
    cursor.execute(
        "INSERT INTO scenarios (name, natural_language_input, nlu_result, project_id) VALUES (?, ?, ?, ?)",
        ("测试场景", test_input, json.dumps(nlu_result), "汇金ERP")
    )
    scenario_id = cursor.lastrowid
    conn.commit()
    print(f"✅ 场景创建成功，ID: {scenario_id}")
    
    # 2. 获取API列表
    print("\n步骤2: 获取API列表")
    cursor.execute("""
        SELECT path, method, summary, description, base_url, parameters, request_body 
        FROM apis 
        WHERE project_id = '汇金ERP'
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print("⚠️  数据库中没有API数据")
        print("   请先导入API数据")
        conn.close()
        return False
    
    apis = []
    for row in rows:
        apis.append({
            "path": row[0],
            "method": row[1],
            "summary": row[2],
            "description": row[3],
            "base_url": row[4],
            "parameters": row[5],
            "request_body": row[6]
        })
    
    print(f"✅ 找到 {len(apis)} 个API")
    for api in apis[:3]:
        print(f"   - {api['method']} {api['path']}")
    
    # 3. AI生成测试用例
    print("\n步骤3: AI生成测试用例")
    
    system_prompt = """你是个资深自动化专家。任务：根据【业务意图】和【API列表】，生成 JSON 测试步骤。
关键规则：
1. 必须识别依赖：若 A 返回 data.token，B 需使用，则配置 param_mappings。
2. 特别是鉴权：登录返回的 Token 必须映射到后续接口的 Headers，to_field 通常为 "Authorization"，to_type 为 "headers"。
3. 禁止自引用：步骤N不能引用步骤N自己的数据，from_step必须小于当前步骤。
4. 第一步通常无依赖：第一个步骤（通常是登录）的param_mappings应该为空[]。
5. 字段区分：params 放 Body (POST/PUT)，url_params 放 Query String。
6. 真实数据：生成符合逻辑的姓名、手机号等，不要用 {}。
格式：{ "scenario_name": "...", "steps": [{ "step_order": 1, "api_path": "...", "api_method": "...", "params": {}, "url_params": {}, "headers": {}, "param_mappings": [] }] }"""
    
    user_prompt = f"意图: {json.dumps(nlu_result)}\n可用 API: {json.dumps(apis[:10])}"
    
    try:
        print("📡 调用AI生成测试用例...")
        case_result = await ai_client.chat(system_prompt, user_prompt)
        
        print(f"✅ AI生成成功:")
        print(f"   场景名称: {case_result.get('scenario_name')}")
        print(f"   步骤数量: {len(case_result.get('steps', []))}")
        
        # 显示步骤
        for step in case_result.get('steps', []):
            print(f"\n   步骤{step.get('step_order')}: {step.get('api_method')} {step.get('api_path')}")
            param_mappings = step.get('param_mappings', [])
            if param_mappings:
                print(f"      参数映射:")
                for mapping in param_mappings:
                    print(f"        - 从步骤{mapping.get('from_step')}的{mapping.get('from_field')} -> {mapping.get('to_type')}.{mapping.get('to_field')}")
            else:
                print(f"      无参数映射")
        
        # 4. 保存测试用例
        print("\n步骤4: 保存测试用例")
        cursor.execute(
            "INSERT INTO test_cases (name, steps, project_id) VALUES (?, ?, ?)",
            (case_result.get("scenario_name"), json.dumps(case_result.get("steps")), "汇金ERP")
        )
        case_id = cursor.lastrowid
        
        cursor.execute("UPDATE scenarios SET test_case_id = ? WHERE id = ?", (case_id, scenario_id))
        conn.commit()
        
        print(f"✅ 测试用例保存成功，ID: {case_id}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ AI生成失败:")
        print(f"   错误: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scenario_generation())
    
    if success:
        print("\n" + "=" * 80)
        print("✅ 场景生成测试成功!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ 场景生成测试失败")
        print("=" * 80)
    
    sys.exit(0 if success else 1)
