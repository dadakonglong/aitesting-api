-- 定时任务系统数据库表
-- 创建时间: 2026-01-28

-- 定时任务表
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    project_id TEXT NOT NULL,
    scenario_id INTEGER NOT NULL,
    cron_expression TEXT NOT NULL,
    environment_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    notify_on_failure BOOLEAN DEFAULT 0,
    notification_config TEXT,  -- JSON格式: {"type": "email", "recipients": [...]}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES test_scenarios(id)
);

-- 任务执行历史表
CREATE TABLE IF NOT EXISTS job_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    execution_id INTEGER,  -- 关联test_executions表
    status TEXT NOT NULL,  -- running, success, failed
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    total_steps INTEGER,
    passed_steps INTEGER,
    failed_steps INTEGER,
    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id),
    FOREIGN KEY (execution_id) REFERENCES test_executions(id)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id ON job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_started_at ON job_executions(started_at);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_project_id ON scheduled_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_is_active ON scheduled_jobs(is_active);
