"""
飞书通知服务

支持发送飞书卡片消息到指定的Webhook
"""

import httpx
import json
from datetime import datetime
from typing import Dict, Optional


class FeishuNotifier:
    """飞书通知服务"""
    
    def __init__(self):
        self.timeout = 10.0
    
    async def send_execution_result(
        self,
        webhook_url: str,
        task_name: str,
        scenario_name: str,
        execution_result: Dict,
        error_message: Optional[str] = None
    ) -> bool:
        """
        发送任务执行结果通知
        
        Args:
            webhook_url: 飞书机器人Webhook URL
            task_name: 任务名称
            scenario_name: 场景名称
            execution_result: 执行结果 {
                "status": "success" | "failed",
                "total_steps": 5,
                "passed_steps": 5,
                "failed_steps": 0,
                "started_at": "2026-02-05 09:00:00",
                "completed_at": "2026-02-05 09:01:30"
            }
            error_message: 错误信息（如果有）
        
        Returns:
            bool: 发送是否成功
        """
        try:
            # 判断执行状态
            is_success = execution_result.get('status') == 'success' and execution_result.get('failed_steps', 0) == 0
            
            # 构建卡片消息
            card = self._build_card_message(
                task_name=task_name,
                scenario_name=scenario_name,
                is_success=is_success,
                execution_result=execution_result,
                error_message=error_message
            )
            
            # 发送到飞书
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                response = await client.post(
                    webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        print(f"✅ 飞书通知发送成功: {task_name}")
                        return True
                    else:
                        print(f"❌ 飞书通知发送失败: {result.get('msg')}")
                        return False
                else:
                    print(f"❌ 飞书通知请求失败: HTTP {response.status_code}")
                    return False
        
        except Exception as e:
            import traceback
            print(f"❌ 发送飞书通知异常: {type(e).__name__}: {str(e)}")
            print(f"📋 异常详情:\n{traceback.format_exc()}")
            return False
    
    def _build_card_message(
        self,
        task_name: str,
        scenario_name: str,
        is_success: bool,
        execution_result: Dict,
        error_message: Optional[str] = None
    ) -> Dict:
        """构建飞书卡片消息"""
        
        # 标题和颜色
        if is_success:
            title = "✅ 定时任务执行成功"
            template = "green"
            status_text = "**状态**: 成功 ✓"
        else:
            title = "❌ 定时任务执行失败"
            template = "red"
            status_text = "**状态**: 失败 ✗"
        
        # 执行时间
        started_at = execution_result.get('started_at', '')
        completed_at = execution_result.get('completed_at', '')
        
        # 步骤统计
        total_steps = execution_result.get('total_steps', 0)
        passed_steps = execution_result.get('passed_steps', 0)
        failed_steps = execution_result.get('failed_steps', 0)
        
        # 构建内容
        content_lines = [
            f"**任务名称**: {task_name}",
            f"**测试场景**: {scenario_name}",
            status_text,
            f"**开始时间**: {started_at}",
            f"**完成时间**: {completed_at}",
            f"**总步骤数**: {total_steps}",
            f"**通过步骤**: {passed_steps}",
            f"**失败步骤**: {failed_steps}"
        ]
        
        # 如果有错误信息，添加到内容中
        if error_message:
            content_lines.append(f"**错误信息**: {error_message}")
        
        content = "\n".join(content_lines)
        
        # 构建卡片
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": title,
                        "tag": "plain_text"
                    },
                    "template": template
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": content,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        }
        
        return card
    
    async def test_webhook(self, webhook_url: str) -> bool:
        """
        测试Webhook是否可用
        
        Args:
            webhook_url: 飞书机器人Webhook URL
        
        Returns:
            bool: Webhook是否可用
        """
        try:
            test_message = {
                "msg_type": "text",
                "content": {
                    "text": "🔔 飞书通知测试消息\n\n这是一条测试消息，用于验证Webhook配置是否正确。"
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                response = await client.post(
                    webhook_url,
                    json=test_message,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('code') == 0
                else:
                    return False
        
        except Exception as e:
            print(f"❌ 测试飞书Webhook异常: {e}")
            return False


    async def send_healing_result(
        self,
        webhook_url: str,
        task_name: str,
        heal_status: str,
        analysis: dict,
        heal_result: dict
    ) -> bool:
        """
        发送自愈结果通知

        Args:
            webhook_url: 飞书机器人Webhook URL
            task_name: 任务名称
            heal_status: auto_healed / manual_needed / failed
            analysis: 根因分析结果
            heal_result: 修复结果
        """
        try:
            status_map = {
                "auto_healed": ("🤖 自愈成功", "green", "已自动修复"),
                "manual_needed": ("👤 需要人工介入", "yellow", "无法自动修复，请人工检查"),
                "failed": ("❌ 自愈失败", "red", "自愈流程异常"),
            }
            title, template, status_text = status_map.get(heal_status, ("❓ 自愈结果未知", "grey", "未知"))

            # 提取根因信息
            analysis_list = analysis.get("analysis", []) if isinstance(analysis, dict) else []
            root_cause_lines = []
            for item in analysis_list[:3]:  # 最多展示3个
                if isinstance(item, dict):
                    root_cause_lines.append(
                        f"• **{item.get('failure_type', '未知类型')}**: {item.get('root_cause', '')[:100]}"
                    )

            content_lines = [
                f"**任务名称**: {task_name}",
                f"**自愈状态**: {status_text}",
                f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
            if root_cause_lines:
                content_lines.append("**根因分析**:")
                content_lines.extend(root_cause_lines)

            heal_msg = heal_result.get("message", "") if isinstance(heal_result, dict) else ""
            if heal_msg:
                content_lines.append(f"**修复说明**: {heal_msg}")

            card = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"content": title, "tag": "plain_text"},
                        "template": template
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"content": "\n".join(content_lines), "tag": "lark_md"}
                        },
                        {"tag": "hr"},
                        {
                            "tag": "note",
                            "elements": [{"tag": "plain_text", "content": f"AI Testing Platform · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]
                        }
                    ]
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                response = await client.post(webhook_url, json=card, headers={"Content-Type": "application/json"})
                if response.status_code == 200:
                    result = response.json()
                    return result.get('code') == 0
                return False
        except Exception as e:
            print(f"❌ 发送自愈通知异常: {e}")
            return False

    async def send_performance_alert(
        self,
        webhook_url: str,
        task_name: str,
        degradation_info: dict
    ) -> bool:
        """
        发送性能劣化告警通知

        Args:
            webhook_url: 飞书机器人Webhook URL
            task_name: 任务名称
            degradation_info: detect_degradation() 返回的劣化信息
        """
        try:
            title = f"⚠️ 性能劣化告警 - {task_name}"
            content_lines = [
                f"**任务名称**: {task_name}",
                f"**告警类型**: 执行耗时异常",
                f"**基线均值**: {degradation_info.get('baseline_avg_ms', 0)} ms",
                f"**近期均值**: {degradation_info.get('recent_avg_ms', 0)} ms",
                f"**变化幅度**: +{degradation_info.get('change_pct', 0):.1f}%",
                f"**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]

            card = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"content": title, "tag": "plain_text"},
                        "template": "orange"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"content": "\n".join(content_lines), "tag": "lark_md"}
                        },
                        {"tag": "hr"},
                        {
                            "tag": "note",
                            "elements": [{"tag": "plain_text", "content": "AI Testing Platform 趋势监控"}]
                        }
                    ]
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                response = await client.post(webhook_url, json=card, headers={"Content-Type": "application/json"})
                if response.status_code == 200:
                    result = response.json()
                    return result.get('code') == 0
                return False
        except Exception as e:
            print(f"❌ 发送性能告警异常: {e}")
            return False


# 全局实例
feishu_notifier = FeishuNotifier()

