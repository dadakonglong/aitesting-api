-- 趋势监控 + 自愈闭环 数据库迁移
-- 创建时间: 2026-02-26

-- 1. 为 job_executions 表增加 duration_ms 字段（总执行耗时）
-- SQLite 不支持 ADD COLUMN IF NOT EXISTS，使用 try/ignore 方式处理
CREATE TABLE IF NOT EXISTS _migration_005_applied (done INTEGER);

-- 2. 任务执行趋势记录表
CREATE TABLE IF NOT EXISTS job_performance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    execution_id INTEGER,               -- 关联 job_executions.id
    executed_at TIMESTAMP NOT NULL,     -- 执行时间（用于按天聚合）
    duration_ms INTEGER DEFAULT 0,      -- 总执行耗时（毫秒）
    total_steps INTEGER DEFAULT 0,
    passed_steps INTEGER DEFAULT 0,
    failed_steps INTEGER DEFAULT 0,
    status TEXT NOT NULL,               -- success / failed
    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id)
);

-- 3. 自愈记录表
CREATE TABLE IF NOT EXISTS job_healing_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    execution_id INTEGER,               -- 触发自愈的那次执行 id
    triggered_at TIMESTAMP NOT NULL,    -- 触发自愈的时间
    completed_at TIMESTAMP,
    status TEXT NOT NULL,               -- analyzing / auto_healed / manual_needed / failed
    root_cause TEXT,                    -- 根因分析结论（JSON）
    heal_result TEXT,                   -- 修复结果（JSON）
    error_message TEXT,                 -- 自愈过程中的异常信息（如有）
    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id)
);

-- 4. 索引优化
CREATE INDEX IF NOT EXISTS idx_perf_records_job_id ON job_performance_records(job_id);
CREATE INDEX IF NOT EXISTS idx_perf_records_executed_at ON job_performance_records(executed_at);
CREATE INDEX IF NOT EXISTS idx_healing_records_job_id ON job_healing_records(job_id);
CREATE INDEX IF NOT EXISTS idx_healing_records_triggered_at ON job_healing_records(triggered_at);
