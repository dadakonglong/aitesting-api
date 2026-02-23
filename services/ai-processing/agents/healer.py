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

    def _extract_fields_for_classify(self, case_name: str) -> List[str]:
        """从用例名中提取应当缺少的字段名（用于分类时核实）"""
        import re
        patterns = [
            r'缺少(?:必要|必填|必须|关键)?(?:字段|参数|属性)[：:\s]*([a-zA-Z_][a-zA-Z0-9_,，\s]*)',
            r'missing\s+(?:required\s+)?(?:field\s+)?([a-zA-Z_][a-zA-Z0-9_,\s]+)',
        ]
        fields = []
        for pattern in patterns:
            m = re.search(pattern, case_name, re.IGNORECASE)
            if m:
                for f in re.split(r'[,，\s]+', m.group(1).strip()):
                    f = f.strip()
                    if f and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', f):
                        fields.append(f)
        return fields

    def _classify_heal_action(self, case: Dict, step: Dict) -> str:
        """
        判断对某个失败用例应采取的修复动作：
        - 'fix_request'      : 请求本身有问题（含了不该有的字段，或缺少正确的认证/参数）
        - 'api_no_validate'  : 接口未做参数校验（字段已缺失但接口返回了成功），需人工介入
        - 'fix_assertion'    : 可修复断言/期望配置
        """
        case_name = (case.get("name") or "")
        expected_status = int((case.get("expected_template") or {}).get("status_code") or 200)
        actual_status = int(step.get("status_code") or 0)
        # 实际请求 params（执行结果中记录的真实发送数据）
        actual_params = step.get("params") or step.get("request_data") or {}

        # 场景一：期望 4xx 但实际收到 2xx
        if expected_status >= 400 and 0 < actual_status < 400:
            # 检查是否是"缺少字段X"用例：若字段 X 已经不在请求里，说明接口本身没有做校验
            missing_fields = self._extract_fields_for_classify(case_name)
            if missing_fields:
                fields_still_present = [f for f in missing_fields if f in actual_params]
                if not fields_still_present:
                    # 字段已经缺失，但接口没有返回错误 → 接口未做校验，无法自动修复
                    return "api_no_validate"
                else:
                    # 字段仍在请求中 → 请求本身有问题，需要删除这些字段
                    return "fix_request"
            # 非"缺少字段"类用例：期望 4xx 但收到 2xx → 请求参数配置有问题
            return "fix_request"

        # 场景二：正向用例期望 2xx 但收到 4xx/5xx → 请求参数有问题
        if expected_status < 400 and actual_status >= 400:
            return "fix_request"

        # 场景三：状态码符合预期，但断言字段不对 → 修断言
        return "fix_assertion"

    def _extract_fields_from_case_name(self, case_name: str) -> List[str]:
        """从用例名中提取应当被删除的字段名，如「缺少必要字段phone」→ ['phone']"""
        import re
        patterns = [
            r'缺少(?:必要|必填|必须|关键)?(?:字段|参数|属性)[：:\s]*([a-zA-Z_][a-zA-Z0-9_,，\s]*)',
            r'missing\s+(?:required\s+)?(?:field\s+)?([a-zA-Z_][a-zA-Z0-9_,\s]+)',
            r'without\s+([a-zA-Z_][a-zA-Z0-9_]+)',
            r'no\s+([a-zA-Z_][a-zA-Z0-9_]+)\s+(?:field|param)',
        ]
        fields = []
        for pattern in patterns:
            m = re.search(pattern, case_name, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                for f in re.split(r'[,，\s]+', raw):
                    f = f.strip()
                    if f and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', f):
                        fields.append(f)
        return fields

    def _apply_fix_request_programmatic(self, plan: Dict, plan_cases: List[tuple], heal_actions: Dict[int, str]) -> Dict:
        """
        对 fix_request 类型的用例，直接从 request_template.params 删除用例名中指定的字段。
        不依赖 AI，确保修复结果可靠。
        返回修改后的 plan（deep copy）。
        """
        import copy
        healed = copy.deepcopy(plan)
        ep_idx = 0
        case_idx_map: List[tuple] = []  # [(ep_in_healed_idx, case_in_ep_idx, non_dep_idx)]
        non_dep_idx = 0
        for ei, ep in enumerate(healed.get("endpoints") or []):
            for ci, case in enumerate(ep.get("cases") or []):
                case_idx_map.append((ei, ci, non_dep_idx))
                non_dep_idx += 1

        for ei, ci, ndi in case_idx_map:
            action = heal_actions.get(ndi)
            if action != "fix_request":
                continue
            _, orig_case = plan_cases[ndi]
            case_name = orig_case.get("name") or ""
            fields_to_remove = self._extract_fields_from_case_name(case_name)
            if not fields_to_remove:
                continue
            case_obj = healed["endpoints"][ei]["cases"][ci]
            params = (case_obj.get("request_template") or {}).get("params")
            if isinstance(params, dict):
                removed = [f for f in fields_to_remove if f in params]
                for f in fields_to_remove:
                    params.pop(f, None)
                if removed:
                    print(f"[Healer] fix_request 删除字段 {removed} from 用例「{case_name}」")
        return healed

    async def heal_single_api_plan(self, execution_result: Dict, plan: Dict) -> Dict:
        """
        修复单接口测试计划（phase2_plan），不写库，返回修复后的 plan 供前端合并。
        用于接口用例 Tab 的自愈。
        """
        analysis = await self.analyze_failure(execution_result)
        if not analysis.get("healable", False):
            return {
                "status": "cannot_heal",
                "message": "失败原因需要人工介入",
                "analysis": analysis
            }
        steps = execution_result.get("steps") or []
        plan_cases = []
        for ep in plan.get("endpoints") or []:
            for c in ep.get("cases") or []:
                plan_cases.append((ep, c))
        non_dep_steps = [s for s in steps if not s.get("is_dep_step")]
        if len(non_dep_steps) != len(plan_cases):
            return {
                "status": "cannot_heal",
                "message": "执行步骤与计划用例数量不一致，无法精确修复",
                "analysis": analysis
            }

        # 预先分类每个失败用例的修复动作，过滤掉无法自愈的
        heal_actions: Dict[int, str] = {}
        skip_cases: List[str] = []
        api_no_validate_cases: List[str] = []
        for i, (step, (ep, case)) in enumerate(zip(non_dep_steps, plan_cases)):
            if not step.get("success"):
                action = self._classify_heal_action(case, step)
                heal_actions[i] = action
                if action == "skip":
                    skip_cases.append(case.get("name") or f"用例{i+1}")
                elif action == "api_no_validate":
                    api_no_validate_cases.append(case.get("name") or f"用例{i+1}")

        if skip_cases:
            return {
                "status": "cannot_heal",
                "message": f"以下用例逻辑有误，建议重新生成：{', '.join(skip_cases)}",
                "analysis": analysis
            }

        if api_no_validate_cases:
            return {
                "status": "cannot_heal",
                "message": (
                    f"以下健壮用例字段已正确缺失，但接口未返回预期的错误响应，"
                    f"说明该接口对此参数缺失未做校验，属于接口自身的 Bug，需人工介入：\n"
                    f"{chr(10).join('  • ' + n for n in api_no_validate_cases)}"
                ),
                "analysis": analysis,
                "heal_actions": heal_actions,
            }

        # 将 fix_request 分类结论覆盖到分析条目，使前端展示正确诊断
        # analysis["analysis"] 按 failed_steps 顺序排列，而 heal_actions 按 non_dep_steps 的索引
        failed_non_dep_indices = [i for i, s in enumerate(non_dep_steps) if not s.get("success")]
        analysis_items = analysis.get("analysis") or []
        for j, non_dep_idx in enumerate(failed_non_dep_indices):
            action = heal_actions.get(non_dep_idx)
            if action not in ("fix_request", "api_no_validate"):
                continue
            if j >= len(analysis_items):
                continue
            _, case = plan_cases[non_dep_idx]
            case_name = case.get("name") or f"用例{non_dep_idx+1}"
            expected_status = (case.get("expected_template") or {}).get("status_code", "4xx")
            if action == "fix_request":
                analysis_items[j] = {
                    "failure_type": "健壮性用例-请求参数错误",
                    "root_cause": (
                        f"「{case_name}」是错误场景测试，期望返回 {expected_status}，"
                        f"但请求中仍包含了不该存在的字段，导致接口正常处理并返回了成功响应。"
                        f"需要从请求中删除该字段。"
                    ),
                    "can_heal": True,
                    "suggested_fix": "从请求参数中删除用例名中提及的必填字段，使接口真正触发预期错误",
                    "patch_hint": "修复请求（删除多余字段），禁止修改期望状态码",
                }
            elif action == "api_no_validate":
                analysis_items[j] = {
                    "failure_type": "接口未做参数校验",
                    "root_cause": (
                        f"「{case_name}」中指定字段已正确从请求中移除，"
                        f"但接口在缺少该字段时仍返回了成功响应（HTTP {(case.get('expected_template') or {}).get('status_code', '4xx')} 期望未被触发）。"
                        f"这是接口自身的 Bug：未对该必填参数进行校验。"
                    ),
                    "can_heal": False,
                    "suggested_fix": "此问题属于接口 Bug，需开发人员在后端添加参数校验逻辑",
                    "patch_hint": "无法自动修复，需人工介入",
                }
        analysis["analysis"] = analysis_items

        # 1. 先用代码直接修复 fix_request 类型（删除多余字段），结果可靠
        programmatically_fixed_plan = self._apply_fix_request_programmatic(plan, plan_cases, heal_actions)

        # 2. 再让 AI 对剩余失败（fix_assertion 类型）和无法程序化处理的情况做进一步修复
        healed_plan = await self._heal_plan_with_analysis(
            programmatically_fixed_plan, plan_cases, non_dep_steps, analysis, heal_actions
        )
        return {
            "status": "healed",
            "message": "计划已修复，请重新执行验证",
            "healed_plan": healed_plan,
            "analysis": analysis,
            "heal_actions": heal_actions,
        }

    async def _heal_plan_with_analysis(
        self,
        plan: Dict,
        plan_cases: List[tuple],
        steps: List[Dict],
        analysis: Dict,
        heal_actions: Optional[Dict[int, str]] = None,
    ) -> Dict:
        """根据失败分析修复 plan 中的 cases"""
        import copy
        healed = copy.deepcopy(plan)
        failed_indices = [i for i, s in enumerate(steps) if not s.get("success")]
        if not failed_indices:
            return healed

        # 为每个失败用例生成修复指令说明
        case_instructions = []
        for i in failed_indices:
            _, case = plan_cases[i]
            action = (heal_actions or {}).get(i, "fix_assertion")
            case_name = case.get("name") or f"用例{i+1}"
            case_type = case.get("case_type") or "unknown"
            if action == "fix_request":
                case_instructions.append(
                    f"- 用例[{i}]「{case_name}」(case_type={case_type})：【修复请求】"
                    f"该用例是错误测试，期望 {(case.get('expected_template') or {}).get('status_code','4xx')} 但收到了成功响应，"
                    f"说明请求中包含了不该有的字段。请从 request_template.params 中删除用例名中提及的多余字段，"
                    f"使请求能真正触发错误。禁止修改 expected_template。"
                )
            else:
                case_instructions.append(
                    f"- 用例[{i}]「{case_name}」(case_type={case_type})：【修复断言/请求参数】"
                    f"可修改 request_template 或 expected_template 以修正失败。"
                    f"但如果 expected_template.status_code 是 4xx/5xx，禁止将其改为 2xx。"
                )

        system_prompt = """你是一个接口测试计划修复专家。
根据失败分析和修复指令，精准修复 plan 中对应失败用例。
只修改导致失败的用例，保持其他用例不变。

核心原则（必须遵守）：
1. 健壮性/边界用例（case_type 含 robustness/boundary，或用例名含"缺少/无效/错误/异常"等）：
   - 若期望状态码为 4xx/5xx，禁止将其改为 2xx，这会使测试失去意义
   - 应修复 request_template，删除不该有的字段，使请求真正触发预期错误
2. 正向用例（case_type=positive）：
   - 优先修复断言或请求参数以匹配正确响应
3. 不要删除或修改 sessionId、venueId、employeeId、token 等前置依赖字段

返回完整的 plan JSON，格式与输入一致，包含 endpoints 数组，每个 endpoint 有 path、method、cases。
每个 case 有 request_template（params、headers、url_params）、expected_template（status_code、response_body）、case_type、name 等。
"""
        user_prompt = f"""当前计划:
{json.dumps(plan, ensure_ascii=False, indent=2)}

失败步骤索引(0-based): {failed_indices}

每个失败用例的修复指令:
{chr(10).join(case_instructions)}

失败分析:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

对应失败步骤详情:
{json.dumps([steps[i] for i in failed_indices], ensure_ascii=False, indent=2)}

请严格按照修复指令返回修复后的完整 plan JSON。"""
        response = await self.ai_client.chat(system_prompt, user_prompt)
        if isinstance(response, dict) and "endpoints" in response:
            return response
        if isinstance(response, str):
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict) and "endpoints" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
        return healed

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
