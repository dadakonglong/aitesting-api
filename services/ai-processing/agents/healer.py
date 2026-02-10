"""
API Healer - 自愈专家
当测试失败时自动分析根因并修复脚本
"""
from typing import Dict, List, Optional
import json
from datetime import datetime

class HealerAgent:
    def __init__(self, ai_client, db_path: str):
        self.ai_client = ai_client
        self.db_path = db_path
    
    async def analyze_failure(self, execution_result: Dict) -> Dict:
        """
        分析测试失败的原因
        
        Args:
            execution_result: 测试执行结果
        
        Returns:
            失败分析报告
        """
        failed_steps = [
            step for step in execution_result.get("steps", [])
            if not step.get("success", False)
        ]
        
        if not failed_steps:
            return {"status": "no_failure", "message": "测试全部通过"}
        
        analysis = []
        for step in failed_steps:
            step_analysis = await self._analyze_step_failure(step)
            analysis.append(step_analysis)
        
        return {
            "status": "analyzed",
            "failed_count": len(failed_steps),
            "analysis": analysis,
            "healable": any(a.get("can_heal", False) for a in analysis)
        }
    
    async def _analyze_step_failure(self, step: Dict) -> Dict:
        """分析单个步骤的失败原因（兼容 execution results 的 step 格式）"""
        system_prompt = """你是一个接口测试自愈专家。
        分析测试步骤失败的原因，并判断是否可以自动修复。

        常见失败类型:
        1. 接口路径变更 (可自愈)
        2. 参数名称/请求体变更 (可自愈)
        3. 响应结构或状态码变更 (可自愈，如期望 200 实际 201)
        4. 断言/期望配置错误 (可自愈)
        5. 鉴权/Token 失效或缺失 (可自愈：更新 token 映射)
        6. 业务逻辑错误或环境不可用 (不可自愈，需人工介入)

        返回 JSON 格式:
        {
            "failure_type": "类型简述",
            "root_cause": "根本原因说明",
            "can_heal": true 或 false,
            "suggested_fix": "具体修复建议（人可读）",
            "patch_hint": "可选，结构化修复提示，如: 更新期望状态码为xxx / 更新请求头Authorization / 更新path 等"
        }
        """
        params = step.get("params") or step.get("request_data") or {}
        api_method = step.get("api_method") or step.get("method", "")
        api_path = step.get("api_path") or step.get("url", "")
        status_code = step.get("status_code")
        error_msg = step.get("error_msg") or step.get("error") or ""
        assertions = step.get("assertions", [])
        response_body = step.get("response")
        expected_status = step.get("expected_status")

        user_prompt = f"""测试步骤信息:
API: {api_method} {api_path}
请求参数/Body: {json.dumps(params, ensure_ascii=False, default=str)}
请求头(如有): {json.dumps(step.get('request_headers') or step.get('headers') or {}, ensure_ascii=False)}
实际响应状态码: {status_code}
期望状态码(如有): {expected_status}
错误信息: {error_msg}
断言/期望(如有): {json.dumps(assertions, ensure_ascii=False)}
实际响应体(片段): {json.dumps(response_body, ensure_ascii=False, default=str)[:800] if response_body else '无'}
请分析失败原因并给出是否可自愈及修复建议。
"""
        response = await self.ai_client.chat(system_prompt, user_prompt)
        return response
    
    async def heal(self, test_case_id: int, execution_result: Dict) -> Dict:
        """
        自动修复失败的测试用例
        
        Args:
            test_case_id: 测试用例ID
            execution_result: 执行结果
        
        Returns:
            修复结果
        """
        # 1. 分析失败原因
        analysis = await self.analyze_failure(execution_result)
        
        if not analysis.get("healable", False):
            return {
                "status": "cannot_heal",
                "message": "失败原因需要人工介入",
                "analysis": analysis
            }
        
        # 2. 获取当前测试用例
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,))
        test_case = cursor.fetchone()
        
        if not test_case:
            conn.close()
            return {"status": "error", "message": "测试用例不存在"}
        
        original_steps = json.loads(test_case["steps"])
        
        # 3. 获取最新的API定义
        project_id = test_case["project_id"]
        cursor.execute("SELECT * FROM apis WHERE project_id = ?", (project_id,))
        current_apis = [dict(row) for row in cursor.fetchall()]
        
        # 4. AI 修复
        healed_steps = await self._heal_steps(
            original_steps,
            current_apis,
            analysis
        )
        
        # 5. 保存修复后的版本
        cursor.execute("""
            UPDATE test_cases 
            SET steps = ? 
            WHERE id = ?
        """, (json.dumps(healed_steps), test_case_id))
        
        # 6. 记录修复历史
        cursor.execute("""
            INSERT INTO healing_records 
            (test_case_id, original_steps, healed_steps, analysis, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            test_case_id,
            json.dumps(original_steps),
            json.dumps(healed_steps),
            json.dumps(analysis),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "healed",
            "message": "测试用例已自动修复",
            "changes": self._diff_steps(original_steps, healed_steps),
            "healed_steps": healed_steps
        }
    
    async def _heal_steps(
        self,
        original_steps: List[Dict],
        current_apis: List[Dict],
        analysis: Dict
    ) -> List[Dict]:
        """使用AI修复测试步骤"""
        system_prompt = """你是一个测试用例修复专家。
        根据失败分析和最新的API定义,修复测试步骤。
        
        修复原则:
        1. 保持测试意图不变
        2. 更新API路径、参数名称以匹配最新定义
        3. 调整断言以适应新的响应结构
        4. 保持参数映射关系的正确性
        
        返回修复后的完整步骤列表(JSON格式)。
        """
        
        user_prompt = f"""原始步骤:
{json.dumps(original_steps, ensure_ascii=False, indent=2)}

最新API定义:
{json.dumps(current_apis, ensure_ascii=False, indent=2)}

失败分析:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

请修复步骤并返回完整的JSON。
"""
        
        response = await self.ai_client.chat(system_prompt, user_prompt)
        if isinstance(response, list):
            return response
        return response.get("steps", original_steps)
    
    def _diff_steps(self, original: List[Dict], healed: List[Dict]) -> List[Dict]:
        """对比原始和修复后的步骤,生成差异报告"""
        changes = []
        for i, (orig, heal) in enumerate(zip(original, healed)):
            step_changes = []
            
            # 检查路径变更
            if orig.get("api_path") != heal.get("api_path"):
                step_changes.append({
                    "field": "api_path",
                    "old": orig.get("api_path"),
                    "new": heal.get("api_path")
                })
            
            # 检查参数变更
            if orig.get("params") != heal.get("params"):
                step_changes.append({
                    "field": "params",
                    "old": orig.get("params"),
                    "new": heal.get("params")
                })
            
            # 检查断言变更
            if orig.get("assertions") != heal.get("assertions"):
                step_changes.append({
                    "field": "assertions",
                    "old": orig.get("assertions"),
                    "new": heal.get("assertions")
                })
            
            if step_changes:
                changes.append({
                    "step_order": i + 1,
                    "changes": step_changes
                })
        
        return changes

    async def heal_api_case(self, api_test_case_id: int, execution_result: Dict) -> Dict:
        """
        自动修复独立的 API 测试用例 (api_test_cases 表)
        """
        # 1. 分析失败原因
        analysis = await self.analyze_failure(execution_result)
        
        if not analysis.get("healable", False):
            return {
                "status": "cannot_heal",
                "message": "失败原因需要人工介入",
                "analysis": analysis
            }
        
        # 2. 获取当前用例
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_test_cases WHERE id = ?", (api_test_case_id,))
        case = cursor.fetchone()
        
        if not case:
            conn.close()
            return {"status": "error", "message": "接口用例不存在"}
        
        original_request = json.loads(case["request_template"] or "{}")
        original_expected = json.loads(case["expected_template"] or "{}")
        
        # 3. 获取最新 API 定义
        cursor.execute("SELECT * FROM apis WHERE id = ?", (case["api_id"],))
        api_def_row = cursor.fetchone()
        api_def = dict(api_def_row) if api_def_row else {}
        
        # 4. AI 修复
        healed_data = await self._heal_api_template(
            original_request,
            original_expected,
            api_def,
            analysis
        )
        
        # 5. 更新数据库
        new_request = healed_data.get("request_template", original_request)
        new_expected = healed_data.get("expected_template", original_expected)
        
        cursor.execute("""
            UPDATE api_test_cases 
            SET request_template = ?, expected_template = ?, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(new_request, ensure_ascii=False),
            json.dumps(new_expected, ensure_ascii=False),
            datetime.now().isoformat() + "Z",
            api_test_case_id
        ))
        conn.commit()
        conn.close()
        
        return {
            "status": "healed",
            "message": "接口用例已自动修复",
            "healed_request": new_request,
            "healed_expected": new_expected
        }

    async def _heal_api_template(
        self,
        request_template: Dict,
        expected_template: Dict,
        api_def: Dict,
        analysis: Dict
    ) -> Dict:
        """使用 AI 修复单接口用例的模板"""
        system_prompt = """你是一个接口用例修复专家。
        根据失败分析和 API 定义，修复用例的请求模板和期望模板。
        
        输入包含:
        1. 原始请求模板 (request_template)
        2. 原始期望模板 (expected_template)
        3. 失败分析 (analysis)
        4. API 定义 (api_def)
        
        请返回修复后的 JSON，格式必须为:
        {
            "request_template": { ... },
            "expected_template": { ... }
        }
        
        修复策略:
        - 如果是参数错误，修正 request_template 中的 params/body
        - 如果是期望与实际不符且实际是正确的（如状态码变更），修正 expected_template
        - 保持测试意图，仅修正导致失败的部分
        """
        
        user_prompt = f"""原始数据:
Request: {json.dumps(request_template, ensure_ascii=False)}
Expected: {json.dumps(expected_template, ensure_ascii=False)}

API定义:
{json.dumps(api_def, ensure_ascii=False, default=str)}

失败分析:
{json.dumps(analysis, ensure_ascii=False, default=str)}

请提供修复后的 JSON。
"""
        response = await self.ai_client.chat(system_prompt, user_prompt)
        return response
