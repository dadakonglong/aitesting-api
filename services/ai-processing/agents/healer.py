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
        """分析单个步骤的失败原因"""
        system_prompt = """你是一个接口测试自愈专家。
        分析测试步骤失败的原因,并判断是否可以自动修复。
        
        常见失败类型:
        1. 接口路径变更 (可自愈)
        2. 参数名称变更 (可自愈)
        3. 响应结构变更 (可自愈)
        4. 断言配置错误 (可自愈)
        5. 业务逻辑错误 (不可自愈,需人工介入)
        6. 环境问题 (不可自愈)
        
        返回JSON格式:
        {
            "failure_type": "类型",
            "root_cause": "根本原因",
            "can_heal": true/false,
            "suggested_fix": "修复建议"
        }
        """
        
        user_prompt = f"""测试步骤信息:
API: {step.get('api_method')} {step.get('api_path')}
请求参数: {json.dumps(step.get('params', {}), ensure_ascii=False)}
响应状态码: {step.get('status_code')}
错误信息: {step.get('error_msg', '')}
断言结果: {json.dumps(step.get('assertions', []), ensure_ascii=False)}
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
