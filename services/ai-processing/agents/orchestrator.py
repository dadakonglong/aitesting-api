"""
多智能体编排器 (Agent Orchestrator)
负责需求拆解、意图识别和子智能体调度
"""
from typing import Dict, List, Optional
import json
from openai import AsyncOpenAI

class OrchestratorAgent:
    def __init__(self, ai_client):
        self.ai_client = ai_client
        self.available_agents = [
            "analyst",  # 分析专家
            "planner",  # 策划专家
            "executor", # 执行专家
            "healer",   # 自愈专家
            "reporter"  # 报告专家
        ]
    
    async def orchestrate(self, user_request: str, context: Dict = None) -> Dict:
        """
        主编排逻辑:分析用户需求并调度相应的智能体
        
        Args:
            user_request: 用户的自然语言请求
            context: 上下文信息(项目ID、环境等)
        
        Returns:
            编排结果,包含调用的智能体和最终输出
        """
        # 1. 意图识别
        intent = await self._identify_intent(user_request)
        
        # 2. 任务拆解
        tasks = await self._decompose_tasks(user_request, intent)
        
        # 3. 智能体调度
        results = []
        for task in tasks:
            agent_type = task.get("agent")
            if agent_type in self.available_agents:
                result = await self._dispatch_to_agent(agent_type, task, context)
                results.append({
                    "agent": agent_type,
                    "task": task,
                    "result": result
                })
        
        return {
            "intent": intent,
            "tasks": tasks,
            "results": results,
            "summary": await self._generate_summary(results)
        }
    
    async def _identify_intent(self, user_request: str) -> Dict:
        """识别用户意图"""
        system_prompt = """你是一个智能测试助手的意图识别模块。
        分析用户请求,识别其核心意图。
        
        可能的意图类型:
        - generate_test: 生成测试用例
        - analyze_api: 分析接口文档
        - execute_test: 执行测试
        - fix_test: 修复失败的测试
        - generate_report: 生成测试报告
        
        返回JSON格式: {"intent_type": "类型", "confidence": 0.9, "entities": [...]}
        """
        
        response = await self.ai_client.chat(system_prompt, user_request)
        return response
    
    async def _decompose_tasks(self, user_request: str, intent: Dict) -> List[Dict]:
        """任务拆解"""
        system_prompt = """你是任务拆解专家。
        根据用户请求和识别的意图,将其拆解为可执行的子任务。
        
        每个任务包含:
        - agent: 负责的智能体类型
        - action: 具体动作
        - inputs: 输入参数
        - dependencies: 依赖的前序任务
        
        返回JSON格式的任务列表。
        """
        
        user_prompt = f"用户请求: {user_request}\n识别的意图: {json.dumps(intent, ensure_ascii=False)}"
        response = await self.ai_client.chat(system_prompt, user_prompt)
        
        return response.get("tasks", [])
    
    async def _dispatch_to_agent(self, agent_type: str, task: Dict, context: Dict) -> Dict:
        """分发任务到具体的智能体"""
        # 这里是占位符,实际会调用具体的智能体实例
        # 在后续步骤中会实现各个智能体
        return {
            "status": "pending",
            "message": f"智能体 {agent_type} 将在后续实现"
        }
    
    async def _generate_summary(self, results: List[Dict]) -> str:
        """生成执行摘要"""
        summary_parts = []
        for result in results:
            agent = result.get("agent")
            status = result.get("result", {}).get("status", "unknown")
            summary_parts.append(f"{agent}: {status}")
        
        return " | ".join(summary_parts)
