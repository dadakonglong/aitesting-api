"""
定时任务调度服务

使用 APScheduler 实现定时任务调度，包含：
- 基础调度：定时执行测试场景
- 趋势监控：持续采集执行耗时，自动识别性能劣化
- 自愈闭环：失败后自动根因分析 → 修复 → 记录
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict, List, Optional
import sqlite3
import json
from datetime import datetime, timedelta
import httpx
import asyncio
import time


class SchedulerService:
    def __init__(self, db_path: str = "test_platform.db"):
        self.db_path = db_path
        self.scheduler = AsyncIOScheduler()
        self._started = False
        self._ensure_tables()
        print("📅 定时任务调度器已初始化（未启动）")

    def _ensure_tables(self):
        """确保趋势监控和自愈相关表已创建"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # job_performance_records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_performance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    execution_id INTEGER,
                    executed_at TIMESTAMP NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    passed_steps INTEGER DEFAULT 0,
                    failed_steps INTEGER DEFAULT 0,
                    status TEXT NOT NULL
                )
            """)
            # job_healing_records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_healing_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    execution_id INTEGER,
                    triggered_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    root_cause TEXT,
                    heal_result TEXT,
                    error_message TEXT
                )
            """)
            # 为 job_executions 增加 duration_ms（幂等）
            try:
                cursor.execute("ALTER TABLE job_executions ADD COLUMN duration_ms INTEGER DEFAULT 0")
            except Exception:
                pass  # 已存在则忽略
            conn.commit()
        finally:
            conn.close()

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
        执行定时任务（含趋势记录 + 自愈闭环）
        """
        print(f"🚀 开始执行定时任务: {job_id}")
        start_time = time.time()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取任务配置
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
            result = None
            execution_id = None
            error_msg = None
            total_steps = 0
            passed_steps = 0
            failed_steps = 0
            final_status = 'failed'

            try:
                env_name = 'test'
                base_url = ''
                if environment_id:
                    cursor.execute("SELECT env_name, base_url FROM project_environments WHERE id = ?", (environment_id,))
                    env_row = cursor.fetchone()
                    if env_row:
                        env_name, base_url = env_row

                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        "http://localhost:8000/api/v1/executions",
                        json={
                            "test_case_id": str(test_case_id),
                            "environment": env_name,
                            "base_url": base_url
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        execution_id = result.get('id')

                        steps = result.get('results', [])
                        total_steps = len(steps)
                        passed_steps = sum(1 for s in steps if s.get('success') is True)
                        failed_steps = total_steps - passed_steps
                        final_status = 'success' if failed_steps == 0 else 'failed'

                        cursor.execute("""
                            UPDATE job_executions 
                            SET status = ?,
                                completed_at = datetime('now', 'localtime'),
                                execution_id = ?,
                                total_steps = ?,
                                passed_steps = ?,
                                failed_steps = ?,
                                duration_ms = ?
                            WHERE id = ?
                        """, (
                            final_status,
                            execution_id,
                            total_steps,
                            passed_steps,
                            failed_steps,
                            int((time.time() - start_time) * 1000),
                            execution_record_id
                        ))
                        conn.commit()

                        print(f"{'✅' if final_status == 'success' else '⚠️'} 任务 {job_id} 执行完成")
                        print(f"📊 步骤: 总计 {total_steps}, 通过 {passed_steps}, 失败 {failed_steps}")
                    else:
                        raise Exception(f"执行失败: HTTP {response.status_code} - {response.text}")

            except Exception as e:
                error_msg = str(e)
                duration_ms = int((time.time() - start_time) * 1000)
                cursor.execute("""
                    UPDATE job_executions 
                    SET status = 'failed',
                        completed_at = datetime('now', 'localtime'),
                        error_message = ?,
                        duration_ms = ?
                    WHERE id = ?
                """, (error_msg, duration_ms, execution_record_id))
                conn.commit()
                print(f"❌ 任务 {job_id} 执行失败: {error_msg}")

            # =========== 趋势监控：写入性能快照 ===========
            duration_ms = int((time.time() - start_time) * 1000)
            cursor.execute("""
                INSERT INTO job_performance_records 
                (job_id, execution_id, executed_at, duration_ms, total_steps, passed_steps, failed_steps, status)
                VALUES (?, ?, datetime('now', 'localtime'), ?, ?, ?, ?, ?)
            """, (
                job_id,
                execution_record_id,
                duration_ms,
                total_steps,
                passed_steps,
                failed_steps,
                final_status
            ))
            conn.commit()
            print(f"📈 趋势数据已记录: job_id={job_id}, duration={duration_ms}ms, status={final_status}")

            # =========== 自愈闭环：失败时触发 ===========
            if final_status == 'failed' and result is not None:
                print(f"🔧 检测到执行失败，启动自愈流程: job_id={job_id}")
                asyncio.create_task(
                    self._run_self_healing(job_id, execution_record_id, test_case_id, result, conn)
                )
            elif error_msg:
                # 执行本身出错（如网络异常），记录无法自愈
                cursor.execute("""
                    INSERT INTO job_healing_records
                    (job_id, execution_id, triggered_at, completed_at, status, root_cause, error_message)
                    VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'), 'failed', ?, ?)
                """, (
                    job_id,
                    execution_record_id,
                    json.dumps({"failure_type": "执行异常", "root_cause": error_msg, "can_heal": False}),
                    error_msg
                ))
                conn.commit()

            # =========== 发送通知 ===========
            if notification_config:
                notification_result = {
                    'status': final_status,
                    'error': error_msg,
                    'total_steps': total_steps,
                    'passed_steps': passed_steps,
                    'failed_steps': failed_steps,
                    'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_ms': duration_ms
                }
                await self._send_notification(job_id, job_name, scenario_name, notification_config, notification_result)

        finally:
            conn.close()

    async def _run_self_healing(
        self,
        job_id: int,
        execution_record_id: int,
        test_case_id: int,
        execution_result: Dict,
        _conn_unused=None
    ):
        """
        自愈闭环：根因分析 → 自动修复 → 记录结果
        在独立 task 中运行，不阻塞主执行流
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 记录自愈启动
            cursor.execute("""
                INSERT INTO job_healing_records
                (job_id, execution_id, triggered_at, status)
                VALUES (?, ?, datetime('now', 'localtime'), 'analyzing')
            """, (job_id, execution_record_id))
            healing_id = cursor.lastrowid
            conn.commit()

            try:
                # 构建 HealerAgent 所需的 execution_result 格式
                steps = execution_result.get('results', [])
                heal_input = {
                    "steps": [
                        {
                            "api_method": s.get("method", ""),
                            "api_path": s.get("path", "") or s.get("url", ""),
                            "status_code": s.get("status_code"),
                            "success": s.get("success", False),
                            "error_msg": s.get("error", "") or s.get("error_message", ""),
                            "params": s.get("request_data") or s.get("params") or {},
                            "response": s.get("response_body") or s.get("response"),
                            "expected_status": s.get("expected_status", 200),
                            "assertions": s.get("assertions", []),
                        }
                        for s in steps
                    ]
                }

                # 动态导入 HealerAgent（避免循环依赖）
                from agents.healer import HealerAgent
                # 动态构建 ai_client（与主服务一致）
                ai_client = await self._get_ai_client()

                healer = HealerAgent(ai_client=ai_client, db_path=self.db_path)

                # 根因分析
                analysis = await healer.analyze_failure(heal_input)
                print(f"🔍 根因分析完成: healable={analysis.get('healable')}")

                if analysis.get('healable', False):
                    # 尝试自动修复
                    heal_result = await healer.heal(test_case_id, heal_input)
                    heal_status = 'auto_healed' if heal_result.get('status') == 'healed' else 'manual_needed'
                    print(f"🔧 自愈结果: {heal_status}")
                else:
                    heal_result = {"status": "cannot_heal", "message": "需要人工介入"}
                    heal_status = 'manual_needed'
                    print(f"👤 需要人工介入")

                # 更新自愈记录
                cursor.execute("""
                    UPDATE job_healing_records
                    SET completed_at = datetime('now', 'localtime'),
                        status = ?,
                        root_cause = ?,
                        heal_result = ?
                    WHERE id = ?
                """, (
                    heal_status,
                    json.dumps(analysis, ensure_ascii=False),
                    json.dumps(heal_result, ensure_ascii=False),
                    healing_id
                ))
                conn.commit()

                # 发送自愈通知（如已配置webhook）
                cursor.execute("SELECT notification_config, name FROM scheduled_jobs WHERE id = ?", (job_id,))
                job_row = cursor.fetchone()
                if job_row and job_row[0]:
                    try:
                        cfg = json.loads(job_row[0]) if isinstance(job_row[0], str) else job_row[0]
                        if isinstance(cfg, str):
                            cfg = json.loads(cfg)
                        if cfg.get('webhook_url'):
                            from services.feishu_notifier import FeishuNotifier
                            notifier = FeishuNotifier()
                            await notifier.send_healing_result(
                                webhook_url=cfg['webhook_url'],
                                task_name=job_row[1] or f"任务{job_id}",
                                heal_status=heal_status,
                                analysis=analysis,
                                heal_result=heal_result
                            )
                    except Exception as notify_err:
                        print(f"⚠️ 自愈通知发送失败: {notify_err}")

            except Exception as e:
                import traceback
                err = str(e)
                print(f"❌ 自愈流程异常: {err}")
                traceback.print_exc()
                cursor.execute("""
                    UPDATE job_healing_records
                    SET completed_at = datetime('now', 'localtime'),
                        status = 'failed',
                        error_message = ?
                    WHERE id = ?
                """, (err, healing_id))
                conn.commit()

        finally:
            conn.close()

    async def _get_ai_client(self):
        """构建 AI 客户端（与 main_sqlite.py 保持一致）"""
        import os
        from openai import AsyncOpenAI

        class _AiClient:
            def __init__(self):
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "sk-xxx"
                base_url = os.getenv("OPENAI_BASE_URL")
                kwargs = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = AsyncOpenAI(**kwargs)
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            async def chat(self, system_prompt: str, user_prompt: str):
                import json, re
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content or "{}"
                try:
                    return json.loads(content)
                except Exception:
                    # 去掉 markdown 代码块再解析
                    content = re.sub(r"```(?:json)?", "", content).strip()
                    try:
                        return json.loads(content)
                    except Exception:
                        return {}

        return _AiClient()

    # ==================== 趋势监控 ====================

    async def get_performance_trend(self, job_id: int, days: int = 7) -> List[Dict]:
        """
        获取近 N 天的趋势数据（按天聚合）

        Returns:
            [
                {
                    "date": "2026-02-26",
                    "total_runs": 3,
                    "success_rate": 66.7,
                    "avg_duration_ms": 1250,
                    "max_duration_ms": 1800,
                    "failed_runs": 1
                },
                ...
            ]
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    date(executed_at) as date,
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_runs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                    ROUND(AVG(duration_ms), 0) as avg_duration_ms,
                    MAX(duration_ms) as max_duration_ms,
                    MIN(duration_ms) as min_duration_ms
                FROM job_performance_records
                WHERE job_id = ?
                  AND executed_at >= datetime('now', '-' || ? || ' days', 'localtime')
                GROUP BY date(executed_at)
                ORDER BY date ASC
            """, (job_id, days))

            rows = cursor.fetchall()
            result = []
            for row in rows:
                total = row["total_runs"] or 1
                result.append({
                    "date": row["date"],
                    "total_runs": row["total_runs"],
                    "success_runs": row["success_runs"] or 0,
                    "failed_runs": row["failed_runs"] or 0,
                    "success_rate": round((row["success_runs"] or 0) / total * 100, 1),
                    "avg_duration_ms": int(row["avg_duration_ms"] or 0),
                    "max_duration_ms": int(row["max_duration_ms"] or 0),
                    "min_duration_ms": int(row["min_duration_ms"] or 0),
                })
            return result
        finally:
            conn.close()

    async def detect_degradation(self, job_id: int) -> Dict:
        """
        检测性能劣化：对比最近1天 vs 近7天整体均值

        Returns:
            {
                "degraded": bool,
                "baseline_avg_ms": 1200,
                "recent_avg_ms": 1800,
                "change_pct": 50.0,
                "message": "⚠️ 执行耗时较基线上升 50%"
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 近7天均值（基线）
            cursor.execute("""
                SELECT AVG(duration_ms) 
                FROM job_performance_records
                WHERE job_id = ?
                  AND executed_at >= datetime('now', '-7 days', 'localtime')
                  AND status = 'success'
            """, (job_id,))
            baseline_avg = cursor.fetchone()[0] or 0

            # 最近1天均值
            cursor.execute("""
                SELECT AVG(duration_ms)
                FROM job_performance_records
                WHERE job_id = ?
                  AND executed_at >= datetime('now', '-1 day', 'localtime')
                  AND status = 'success'
            """, (job_id,))
            recent_avg = cursor.fetchone()[0] or 0

            if baseline_avg == 0 or recent_avg == 0:
                return {
                    "degraded": False,
                    "baseline_avg_ms": int(baseline_avg),
                    "recent_avg_ms": int(recent_avg),
                    "change_pct": 0,
                    "message": "数据不足，无法判断劣化"
                }

            change_pct = round((recent_avg - baseline_avg) / baseline_avg * 100, 1)
            degraded = change_pct > 30  # 超过30%视为劣化

            message = (
                f"⚠️ 执行耗时较基线上升 {change_pct}%，可能存在性能劣化"
                if degraded
                else f"✅ 执行耗时正常（变化 {change_pct:+.1f}%）"
            )

            return {
                "degraded": degraded,
                "baseline_avg_ms": int(baseline_avg),
                "recent_avg_ms": int(recent_avg),
                "change_pct": change_pct,
                "message": message
            }
        finally:
            conn.close()

    # ==================== 自愈闭环 ====================

    async def get_healing_history(self, job_id: int, limit: int = 20) -> List[Dict]:
        """获取自愈历史列表"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM job_healing_records
                WHERE job_id = ?
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (job_id, limit))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                # 解析 JSON 字段
                for field in ('root_cause', 'heal_result'):
                    if item.get(field) and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except Exception:
                            pass
                result.append(item)
            return result
        finally:
            conn.close()

    async def trigger_manual_heal(self, job_id: int) -> Dict:
        """手动触发自愈：取最近一次失败执行，重新进行根因分析并尝试自动修复"""
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            # 找最近一次失败执行（含 execution_id 关联到 test_executions）
            cursor.execute("""
                SELECT je.id as exec_id, je.execution_id as test_exec_id,
                       je.error_message, ts.test_case_id
                FROM job_executions je
                LEFT JOIN scheduled_jobs sj ON je.job_id = sj.id
                LEFT JOIN scenarios ts ON sj.scenario_id = ts.id
                WHERE je.job_id = ? AND je.status = 'failed'
                ORDER BY je.started_at DESC
                LIMIT 1
            """, (job_id,))
            row = cursor.fetchone()

            if not row:
                return {"status": "error", "message": "没有找到失败的执行记录"}

            exec_id = row["exec_id"]
            test_exec_id = row["test_exec_id"]
            test_case_id = row["test_case_id"]
            error_msg = row["error_message"] or ""

            if not test_case_id:
                return {"status": "error", "message": "找不到关联的测试用例"}

            # 尝试从 API 获取真实执行结果
            real_result = None
            if test_exec_id:
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(f"http://localhost:8000/api/v1/executions/{test_exec_id}")
                        if resp.status_code == 200:
                            real_result = resp.json()
                            print(f"✅ 手动自愈：获取到真实执行结果 exec_id={test_exec_id}")
                except Exception as e:
                    print(f"⚠️ 手动自愈：获取真实执行结果失败: {e}")

            # 如果获取不到真实结果，用 error_message 构造一个 minimal 的失败步骤
            if not real_result or not real_result.get('results'):
                real_result = {
                    "results": [
                        {
                            "success": False,
                            "error": error_msg or "执行失败，详情不可用",
                            "method": "",
                            "path": "",
                            "status_code": None,
                        }
                    ] if error_msg else []
                }

            asyncio.create_task(
                self._run_self_healing(job_id, exec_id, test_case_id, real_result)
            )

            return {"status": "triggered", "message": "自愈流程已启动，请稍后查看自愈历史"}
        finally:
            conn.close()


    # ==================== 原有 CRUD ====================

    async def pause_job(self, job_id: int) -> Dict:
        """暂停任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE scheduled_jobs SET is_active = 0 WHERE id = ?", (job_id,))
            conn.commit()
            try:
                self.scheduler.remove_job(str(job_id))
            except Exception:
                pass
            return {"message": "任务已暂停"}
        finally:
            conn.close()

    async def resume_job(self, job_id: int) -> Dict:
        """恢复任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE scheduled_jobs SET is_active = 1 WHERE id = ?", (job_id,))
            conn.commit()
            cursor.execute("SELECT scenario_id, cron_expression FROM scheduled_jobs WHERE id = ?", (job_id,))
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
            try:
                self.scheduler.remove_job(str(job_id))
            except Exception:
                pass
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
                SELECT je.*, jhr.status as heal_status, jhr.root_cause, jhr.heal_result
                FROM job_executions je
                LEFT JOIN job_healing_records jhr ON jhr.execution_id = je.id
                WHERE je.job_id = ?
                ORDER BY je.started_at DESC
                LIMIT ?
            """, (job_id, limit))
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                for field in ('root_cause', 'heal_result'):
                    if item.get(field) and isinstance(item[field], str):
                        try:
                            item[field] = json.loads(item[field])
                        except Exception:
                            pass
                result.append(item)
            return result
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
            count = 0
            for row in cursor.fetchall():
                job_id, scenario_id, cron = row
                self._add_job_to_scheduler(job_id, {'scenario_id': scenario_id, 'cron': cron})
                count += 1
            print(f"✅ 已加载 {count} 个活跃任务")
        finally:
            conn.close()

    async def update_job(self, job_id: int, job_config: Dict) -> Dict:
        """更新定时任务"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM scheduled_jobs WHERE id = ?", (job_id,))
            if not cursor.fetchone():
                raise ValueError(f"任务 {job_id} 不存在")

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
            self._add_job_to_scheduler(job_id, job_config)
            return {"job_id": job_id, "message": "任务更新成功"}
        finally:
            conn.close()

    # ==================== 通知 ====================

    async def _send_notification(
        self,
        job_id: int,
        job_name: str,
        scenario_name: str,
        notification_config: str,
        result: Dict
    ):
        """发送通知(飞书/邮件/钉钉/企业微信)"""
        try:
            config = {}
            if isinstance(notification_config, str):
                try:
                    config = json.loads(notification_config)
                    if isinstance(config, str):
                        config = json.loads(config)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    return
            else:
                config = notification_config

            if not isinstance(config, dict):
                return

            notification_type = config.get('type', 'none')

            if notification_type == 'feishu':
                webhook_url = config.get('webhook_url')
                if not webhook_url:
                    return
                from services.feishu_notifier import FeishuNotifier
                notifier = FeishuNotifier()
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except Exception:
                        result = {}
                error_message = result.get('error')
                await notifier.send_execution_result(
                    webhook_url=webhook_url,
                    task_name=job_name,
                    scenario_name=scenario_name,
                    execution_result=result,
                    error_message=error_message
                )
            elif notification_type == 'email':
                print(f"📧 发送邮件通知: 任务 {job_id}")
            elif notification_type == 'dingtalk':
                print(f"📱 发送钉钉通知: 任务 {job_id}")
            elif notification_type == 'wechat':
                print(f"💬 发送企业微信通知: 任务 {job_id}")
        except Exception as e:
            print(f"❌ 发送通知失败: {e}")
