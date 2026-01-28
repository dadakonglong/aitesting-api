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
        self.scheduler.start()
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
            # 获取任务配置
            cursor.execute("""
                SELECT scenario_id, environment_id, notify_on_failure, notification_config
                FROM scheduled_jobs WHERE id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if not row:
                print(f"❌ 任务 {job_id} 不存在")
                return
            
            scenario_id, environment_id, notify_on_failure, notification_config = row
            
            # 记录执行开始
            cursor.execute("""
                INSERT INTO job_executions (job_id, status, started_at)
                VALUES (?, 'running', ?)
            """, (job_id, datetime.now()))
            execution_record_id = cursor.lastrowid
            conn.commit()
            
            # 调用场景执行API
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    # 假设场景执行API在本地8000端口
                    response = await client.post(
                        f"http://localhost:8000/api/v1/scenarios/{scenario_id}/execute",
                        json={"environment_id": environment_id} if environment_id else {}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        execution_id = result.get('execution_id')
                        
                        # 更新执行记录
                        cursor.execute("""
                            UPDATE job_executions 
                            SET status = 'success', 
                                completed_at = ?,
                                execution_id = ?,
                                total_steps = ?,
                                passed_steps = ?,
                                failed_steps = ?
                            WHERE id = ?
                        """, (
                            datetime.now(),
                            execution_id,
                            result.get('total_steps', 0),
                            result.get('passed_steps', 0),
                            result.get('failed_steps', 0),
                            execution_record_id
                        ))
                        conn.commit()
                        
                        print(f"✅ 任务 {job_id} 执行成功")
                        
                        # 如果有失败且需要通知
                        if result.get('failed_steps', 0) > 0 and notify_on_failure:
                            await self._send_notification(job_id, notification_config, result)
                    else:
                        raise Exception(f"执行失败: {response.text}")
            
            except Exception as e:
                error_msg = str(e)
                cursor.execute("""
                    UPDATE job_executions 
                    SET status = 'failed', 
                        completed_at = ?,
                        error_message = ?
                    WHERE id = ?
                """, (datetime.now(), error_msg, execution_record_id))
                conn.commit()
                
                print(f"❌ 任务 {job_id} 执行失败: {error_msg}")
                
                if notify_on_failure:
                    await self._send_notification(job_id, notification_config, {"error": error_msg})
        
        finally:
            conn.close()
    
    async def _send_notification(self, job_id: int, notification_config: str, result: Dict):
        """发送通知(邮件/钉钉/企业微信)"""
        try:
            config = json.loads(notification_config) if notification_config else {}
            notification_type = config.get('type', 'none')
            
            if notification_type == 'email':
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
                LEFT JOIN test_scenarios ts ON sj.scenario_id = ts.id
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
