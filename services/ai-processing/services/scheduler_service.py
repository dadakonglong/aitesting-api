"""
定时任务调度服务

使用 APScheduler 实现定时任务调度
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict, List, Optional
import sqlite3
import json
from datetime import datetime
import httpx
import asyncio


class SchedulerService:
    def __init__(self, db_path: str = "test_platform.db"):
        self.db_path = db_path
        self.scheduler = AsyncIOScheduler()
        self._started = False
        print("📅 定时任务调度器已初始化（未启动）")
    
    def start(self):
        """启动调度器"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            print("📅 定时任务调度器已启动")
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    async def create_job(self, job_config: Dict) -> Dict:
        """
        创建定时任务
        
        Args:
            job_config: {
                "name": "每日回归测试",
                "description": "每天凌晨2点执行",
                "scenario_id": 123,
                "project_id": "default-project",
                "cron": "0 2 * * *",
                "environment_id": 1,
                "notify_on_failure": true,
                "notification_config": {"type": "email", "recipients": ["test@example.com"]}
            }
        
        Returns:
            {"job_id": 1, "message": "任务创建成功"}
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 插入数据库
            cursor.execute("""
                INSERT INTO scheduled_jobs 
                (name, description, project_id, scenario_id, cron_expression, 
                 environment_id, is_active, notify_on_failure, notification_config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_config['name'],
                job_config.get('description', ''),
                job_config['project_id'],
                job_config['scenario_id'],
                job_config['cron'],
                job_config.get('environment_id'),
                True,
                job_config.get('notify_on_failure', False),
                json.dumps(job_config.get('notification_config', {}))
            ))
            
            job_id = cursor.lastrowid
            conn.commit()
            
            # 添加到调度器
            self._add_job_to_scheduler(job_id, job_config)
            
            return {"job_id": job_id, "message": "任务创建成功"}
        finally:
            conn.close()
    
    def _add_job_to_scheduler(self, job_id: int, job_config: Dict):
        """将任务添加到APScheduler"""
        try:
            trigger = CronTrigger.from_crontab(job_config['cron'])
            self.scheduler.add_job(
                self.execute_job,
                trigger=trigger,
                id=str(job_id),
                args=[job_id],
                replace_existing=True
            )
            print(f"✅ 任务 {job_id} 已添加到调度器: {job_config['cron']}")
        except Exception as e:
            print(f"❌ 添加任务到调度器失败: {e}")
    
    async def execute_job(self, job_id: int):
        """
        执行定时任务
        
        Args:
            job_id: 任务ID
        """
        print(f"🚀 开始执行定时任务: {job_id}")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取任务配置（包括任务名称和场景名称）
            cursor.execute("""
                SELECT sj.name, sj.scenario_id, sj.environment_id, sj.notification_config,
                       ts.name as scenario_name, ts.test_case_id
                FROM scheduled_jobs sj
                LEFT JOIN scenarios ts ON sj.scenario_id = ts.id
                WHERE sj.id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if not row:
                print(f"❌ 任务 {job_id} 不存在")
                return
            
            job_name, scenario_id, environment_id, notification_config, scenario_name, test_case_id = row
            scenario_name = scenario_name or f"场景ID: {scenario_id}"
            
            if not test_case_id:
                print(f"❌ 场景 {scenario_id} 没有关联的测试用例")
                return
            
            # 记录执行开始
            cursor.execute("""
                INSERT INTO job_executions (job_id, status, started_at)
                VALUES (?, 'running', datetime('now', 'localtime'))
            """, (job_id,))
            execution_record_id = cursor.lastrowid
            conn.commit()
            
            # 调用测试用例执行API
            try:
                # 获取环境信息
                env_name = 'test'
                base_url = ''
                if environment_id:
                    cursor.execute("SELECT env_name, base_url FROM project_environments WHERE id = ?", (environment_id,))
                    env_row = cursor.fetchone()
                    if env_row:
                        env_name, base_url = env_row
                
                async with httpx.AsyncClient(timeout=300.0) as client:
                    # 使用正确的执行API
                    response = await client.post(
                        f"http://localhost:8000/api/v1/executions",
                        json={
                            "test_case_id": str(test_case_id),
                            "environment": env_name,
                            "base_url": base_url
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        execution_id = result.get('id')
                        
                        # 计算步骤统计
                        steps = result.get('results', [])
                        total_steps = len(steps)
                        passed_steps = sum(1 for s in steps if s.get('success') is True)
                        failed_steps = total_steps - passed_steps
                        
                        # 更新执行记录
                        cursor.execute("""
                            UPDATE job_executions 
                            SET status = 'success', 
                                completed_at = datetime('now', 'localtime'),
                                execution_id = ?,
                                total_steps = ?,
                                passed_steps = ?,
                                failed_steps = ?
                            WHERE id = ?
                        """, (
                            execution_id, 
                            total_steps, 
                            passed_steps, 
                            failed_steps, 
                            execution_record_id
                        ))
                        conn.commit()
                        
                        print(f"✅ 任务 {job_id} 执行成功，ID: {execution_id}")
                        print(f"📊 步骤统计: 总计 {total_steps}, 通过 {passed_steps}, 失败 {failed_steps}")
                        
                        # 每次执行都发送通知（不论成功或失败）
                        if notification_config:
                            notification_result = {
                                'status': 'success' if failed_steps == 0 else 'failed',
                                'total_steps': total_steps,
                                'passed_steps': passed_steps,
                                'failed_steps': failed_steps,
                                'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            await self._send_notification(job_id, job_name, scenario_name, notification_config, notification_result)
                    else:
                        raise Exception(f"执行失败: HTTP {response.status_code} - {response.text}")
            
            except Exception as e:
                error_msg = str(e)
                cursor.execute("""
                    UPDATE job_executions 
                    SET status = 'failed', 
                        completed_at = datetime('now', 'localtime'),
                        error_message = ?
                    WHERE id = ?
                """, (error_msg, execution_record_id))
                conn.commit()
                
                print(f"❌ 任务 {job_id} 执行失败: {error_msg}")
                
                # 每次执行都发送通知（包括失败情况）
                if notification_config:
                    notification_result = {
                        'status': 'failed',
                        'error': error_msg,
                        'total_steps': 0,
                        'passed_steps': 0,
                        'failed_steps': 0,
                        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    await self._send_notification(job_id, job_name, scenario_name, notification_config, notification_result)
        
        finally:
            conn.close()
    
    async def _send_notification(self, job_id: int, job_name: str, scenario_name: str, notification_config: str, result: Dict):
        """发送通知(飞书/邮件/钉钉/企业微信)"""
        try:
            # 解析通知配置
            config = {}
            if isinstance(notification_config, str):
                try:
                    config = json.loads(notification_config)
                    # 如果第一次解析后还是字符串，说明被双重编码了，再解析一次
                    if isinstance(config, str):
                        config = json.loads(config)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    return
            else:
                config = notification_config
            
            if not isinstance(config, dict):
                print(f"❌ config不是字典，无法发送通知")
                return
            
            notification_type = config.get('type', 'none')
            
            if notification_type == 'feishu':
                # 飞书通知
                webhook_url = config.get('webhook_url')
                if not webhook_url:
                    print(f"⚠️ 任务 {job_id} 未配置飞书Webhook URL")
                    return
                
                # 导入并实例化飞书通知服务
                from services.feishu_notifier import FeishuNotifier
                notifier = FeishuNotifier()
                
                # 确保result是字典
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        result = {}
                
                # 发送通知
                error_message = result.get('error')
                success = await notifier.send_execution_result(
                    webhook_url=webhook_url,
                    task_name=job_name,
                    scenario_name=scenario_name,
                    execution_result=result,
                    error_message=error_message
                )
                
                if success:
                    print(f"✅ 飞书通知发送成功: {task_name if 'task_name' in locals() else job_name}")
                else:
                    print(f"❌ 飞书通知发送失败")
            elif notification_type == 'email':
                # TODO: 实现邮件通知
                print(f"📧 发送邮件通知: 任务 {job_id}")
            elif notification_type == 'dingtalk':
                # TODO: 实现钉钉通知
                print(f"📱 发送钉钉通知: 任务 {job_id}")
            elif notification_type == 'wechat':
                # TODO: 实现企业微信通知
                print(f"💬 发送企业微信通知: 任务 {job_id}")
        except Exception as e:
            print(f"❌ 发送通知失败: {e}")
    
    async def pause_job(self, job_id: int) -> Dict:
        """暂停任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scheduled_jobs SET is_active = 0 WHERE id = ?
            """, (job_id,))
            conn.commit()
            
            # 从调度器移除
            self.scheduler.remove_job(str(job_id))
            
            return {"message": "任务已暂停"}
        finally:
            conn.close()
    
    async def resume_job(self, job_id: int) -> Dict:
        """恢复任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scheduled_jobs SET is_active = 1 WHERE id = ?
            """, (job_id,))
            conn.commit()
            
            # 重新添加到调度器
            cursor.execute("""
                SELECT scenario_id, cron_expression FROM scheduled_jobs WHERE id = ?
            """, (job_id,))
            row = cursor.fetchone()
            if row:
                scenario_id, cron = row
                self._add_job_to_scheduler(job_id, {'scenario_id': scenario_id, 'cron': cron})
            
            return {"message": "任务已恢复"}
        finally:
            conn.close()
    
    async def delete_job(self, job_id: int) -> Dict:
        """删除任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 从调度器移除
            try:
                self.scheduler.remove_job(str(job_id))
            except:
                pass
            
            # 从数据库删除
            cursor.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()
            
            return {"message": "任务已删除"}
        finally:
            conn.close()
    
    async def get_job_list(self, project_id: str) -> List[Dict]:
        """获取任务列表"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT sj.*, ts.name as scenario_name
                FROM scheduled_jobs sj
                LEFT JOIN scenarios ts ON sj.scenario_id = ts.id
                WHERE sj.project_id = ?
                ORDER BY sj.created_at DESC
            """, (project_id,))
            
            jobs = [dict(row) for row in cursor.fetchall()]
            return jobs
        finally:
            conn.close()
    
    async def get_job_history(self, job_id: int, limit: int = 50) -> List[Dict]:
        """获取任务执行历史"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM job_executions
                WHERE job_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (job_id, limit))
            
            history = [dict(row) for row in cursor.fetchall()]
            return history
        finally:
            conn.close()
    
    async def load_jobs_from_db(self):
        """从数据库加载所有活跃任务到调度器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, scenario_id, cron_expression 
                FROM scheduled_jobs 
                WHERE is_active = 1
            """)
            
            for row in cursor.fetchall():
                job_id, scenario_id, cron = row
                self._add_job_to_scheduler(job_id, {'scenario_id': scenario_id, 'cron': cron})
            
            
            print(f"✅ 已加载 {cursor.rowcount} 个活跃任务")
        finally:
            conn.close()

    async def update_job(self, job_id: int, job_config: Dict) -> Dict:
        """
        更新定时任务
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查任务是否存在
            cursor.execute("SELECT id FROM scheduled_jobs WHERE id = ?", (job_id,))
            if not cursor.fetchone():
                raise ValueError(f"任务 {job_id} 不存在")
            
            # 更新数据库
            cursor.execute("""
                UPDATE scheduled_jobs 
                SET name = ?, description = ?, scenario_id = ?, cron_expression = ?, 
                    environment_id = ?, notify_on_failure = ?, notification_config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                job_config['name'],
                job_config.get('description', ''),
                job_config['scenario_id'],
                job_config['cron'],
                job_config.get('environment_id'),
                job_config.get('notify_on_failure', False),
                json.dumps(job_config.get('notification_config', {})),
                job_id
            ))
            
            conn.commit()
            
            # 更新调度器中的任务
            self._add_job_to_scheduler(job_id, job_config)
            
            return {"job_id": job_id, "message": "任务更新成功"}
        finally:
            conn.close()
