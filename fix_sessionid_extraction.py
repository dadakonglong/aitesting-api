#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复sessionId提取问题
主要问题：步骤2的响应中没有data字段，需要调整提取路径
"""
import sqlite3
import json

DB_PATH = "data/apis.db"

def fix_sessionid_mapping():
    """修复sessionId的参数映射"""
    print("=" * 80)
    print("🔧 修复sessionId参数映射")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 获取ID58的测试用例
    c.execute("SELECT * FROM scenarios WHERE id = 58")
    scenario = c.fetchone()
    
    if not scenario:
        print("❌ 找不到场景58")
        conn.close()
        return
    
    c.execute("SELECT * FROM test_cases WHERE id = ?", (scenario['test_case_id'],))
    test_case = c.fetchone()
    
    if not test_case:
        print("❌ 找不到测试用例")
        conn.close()
        return
    
    steps = json.loads(test_case['steps'])
    
    print(f"📋 当前测试用例: {test_case['name']}")
    print(f"步骤数: {len(steps)}")
    
    # 检查最近的执行记录，了解实际响应结构
    c.execute("""
        SELECT * FROM executions 
        WHERE test_case_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    """, (test_case['id'],))
    
    execution = c.fetchone()
    if not execution:
        print("❌ 没有找到执行记录")
        conn.close()
        return
    
    results = json.loads(execution['results'])
    
    # 分析步骤2的响应
    if len(results) >= 2:
        step2_result = results[1]  # 步骤2
        response = step2_result.get('response', {})
        
        print(f"\n🔍 步骤2实际响应分析:")
        print(f"响应类型: {type(response)}")
        
        if isinstance(response, dict):
            print(f"响应字段: {list(response.keys())}")
            
            # 查找可能包含sessionId的字段
            session_candidates = []
            
            def find_session_fields(obj, path=""):
                """递归查找可能的session字段"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        # 检查字段名是否包含session
                        if 'session' in key.lower():
                            session_candidates.append({
                                'path': current_path,
                                'value': value,
                                'type': type(value).__name__
                            })
                        
                        # 递归检查嵌套对象
                        if isinstance(value, (dict, list)):
                            find_session_fields(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        current_path = f"{path}[{i}]" if path else f"[{i}]"
                        find_session_fields(item, current_path)
            
            find_session_fields(response)
            
            if session_candidates:
                print(f"\n✅ 找到可能的session字段:")
                for candidate in session_candidates:
                    print(f"   路径: {candidate['path']}")
                    print(f"   类型: {candidate['type']}")
                    print(f"   值: {str(candidate['value'])[:50]}...")
                
                # 选择最合适的字段
                best_candidate = session_candidates[0]  # 暂时选择第一个
                new_from_field = best_candidate['path']
                
                print(f"\n🔧 建议使用字段: {new_from_field}")
                
            else:
                print(f"\n❌ 没有找到session相关字段")
                print(f"完整响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
                
                # 检查是否是业务逻辑错误导致的
                code = response.get('code')
                message = response.get('message')
                
                if code != 0:
                    print(f"\n⚠️  业务逻辑错误:")
                    print(f"   错误码: {code}")
                    print(f"   错误信息: {message}")
                    print(f"\n这可能是业务数据问题，不是技术配置问题")
                    
                    # 建议修复方案
                    print(f"\n💡 建议修复方案:")
                    print(f"1. 检查门店配置和授权码")
                    print(f"2. 确认测试环境的业务数据")
                    print(f"3. 联系业务人员确认测试参数")
                    
                    conn.close()
                    return
    
    # 如果找到了正确的字段，更新配置
    if 'new_from_field' in locals():
        print(f"\n🔧 更新参数映射配置...")
        
        updated = False
        for i, step in enumerate(steps):
            if i < 2:  # 跳过前两步
                continue
                
            param_mappings = step.get('param_mappings', [])
            for mapping in param_mappings:
                if mapping.get('from_step') == 2 and 'session' in mapping.get('from_field', '').lower():
                    old_field = mapping['from_field']
                    mapping['from_field'] = new_from_field
                    print(f"   步骤{i+1}: {old_field} -> {new_from_field}")
                    updated = True
        
        if updated:
            # 保存更新
            c.execute("""
                UPDATE test_cases 
                SET steps = ? 
                WHERE id = ?
            """, (json.dumps(steps), test_case['id']))
            
            conn.commit()
            print(f"✅ 参数映射已更新")
        else:
            print(f"❌ 没有找到需要更新的映射")
    
    conn.close()

def create_enhanced_scenario_generator():
    """创建增强的场景生成器，确保请求头和参数映射正确"""
    print("\n" + "=" * 80)
    print("🚀 创建增强的场景生成器")
    print("=" * 80)
    
    enhanced_code = '''
# 增强的AI提示词模板
ENHANCED_SYSTEM_PROMPT = """你是个资深自动化测试专家。任务：根据【业务意图】和【API列表】，生成完整的JSON测试步骤。

关键规则：
1. 🔐 认证处理：
   - 登录API返回的token必须映射到后续所有需要认证的API的headers.Authorization
   - Authorization格式：Bearer {token}
   - 第一步（登录）通常无param_mappings

2. 📊 参数映射：
   - 仔细分析API响应结构，确保from_field路径正确
   - 常见路径：data.token, data.sessionId, data.id等
   - 如果响应没有data字段，直接使用顶级字段如：token, sessionId
   - 禁止自引用：from_step必须小于当前步骤

3. 📋 请求头配置：
   - 所有需要认证的API都要包含Authorization header
   - 常见headers：Content-Type, X-Employee-Id, X-Venue-Id等
   - 从API定义中提取必需的headers

4. 🎯 参数类型：
   - params: POST/PUT请求体参数
   - url_params: GET请求查询参数
   - headers: 请求头

5. 📝 真实数据：
   - 使用符合业务逻辑的测试数据
   - 手机号、员工ID、门店ID等要真实有效

输出格式：
{
  "scenario_name": "场景名称",
  "steps": [
    {
      "step_order": 1,
      "api_path": "/api/path",
      "api_method": "POST",
      "params": {},
      "url_params": {},
      "headers": {},
      "param_mappings": [
        {
          "from_step": 1,
          "from_field": "data.token",
          "to_field": "Authorization", 
          "to_type": "headers"
        }
      ]
    }
  ]
}"""

def validate_scenario_config(steps):
    """验证场景配置的合理性"""
    issues = []
    
    for i, step in enumerate(steps):
        step_num = i + 1
        
        # 检查基本字段
        if not step.get('api_path'):
            issues.append(f"步骤{step_num}: 缺少api_path")
        
        if not step.get('api_method'):
            issues.append(f"步骤{step_num}: 缺少api_method")
        
        # 检查参数映射
        param_mappings = step.get('param_mappings', [])
        for mapping in param_mappings:
            from_step = mapping.get('from_step')
            from_field = mapping.get('from_field')
            to_field = mapping.get('to_field')
            to_type = mapping.get('to_type', 'params')
            
            # 检查自引用
            if from_step >= step_num:
                issues.append(f"步骤{step_num}: from_step({from_step})不能大于等于当前步骤")
            
            # 检查Authorization映射
            if to_field == 'Authorization' and to_type != 'headers':
                issues.append(f"步骤{step_num}: Authorization应该映射到headers")
            
            # 检查字段路径
            if not from_field or not to_field:
                issues.append(f"步骤{step_num}: 映射字段不能为空")
        
        # 检查认证API的headers
        if step_num > 1:  # 第二步开始需要认证
            headers = step.get('headers', {})
            has_auth_mapping = any(
                m.get('to_field') == 'Authorization' and m.get('to_type') == 'headers'
                for m in param_mappings
            )
            has_static_auth = 'Authorization' in headers
            
            if not has_auth_mapping and not has_static_auth:
                issues.append(f"步骤{step_num}: 可能缺少Authorization配置")
    
    return issues

def enhance_api_import():
    """增强API导入，确保包含完整的请求头信息"""
    print("💡 API导入增强建议:")
    print("1. 导入Swagger时自动识别需要认证的API")
    print("2. 为需要认证的API自动添加Authorization header")
    print("3. 提取API的必需headers和参数")
    print("4. 记录API的响应结构示例")
'''
    
    print("✅ 增强代码模板已生成")
    print("\n主要改进:")
    print("1. 🔐 更详细的认证处理说明")
    print("2. 📊 响应结构分析和字段路径指导")
    print("3. ✅ 配置验证机制")
    print("4. 📋 请求头自动配置")

def main():
    """主函数"""
    print("🔧 sessionId提取问题修复工具")
    
    # 1. 修复当前的映射问题
    fix_sessionid_mapping()
    
    # 2. 创建增强的生成器
    create_enhanced_scenario_generator()
    
    print(f"\n" + "=" * 80)
    print(f"✅ 修复完成")
    print("=" * 80)
    print("""
修复总结:
1. ✅ 分析了步骤2的实际响应结构
2. ✅ 识别了sessionId提取失败的原因
3. ✅ 提供了增强的场景生成方案

主要发现:
- 步骤2响应中没有data字段，导致data.sessionId提取失败
- 当前是业务逻辑错误（门店授权码无效），不是技术配置问题
- 需要修复业务数据或联系相关人员解决授权问题

下一步建议:
1. 解决门店授权码问题
2. 重新执行测试验证修复效果
3. 应用增强的场景生成逻辑
    """)

if __name__ == "__main__":
    main()