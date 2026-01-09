-- 初始化数据库脚本

-- 创建项目表
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建测试场景表
CREATE TABLE IF NOT EXISTS scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    natural_language_input TEXT,
    parsed_structure JSONB,
    status VARCHAR(50) DEFAULT 'draft',
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建测试用例表
CREATE TABLE IF NOT EXISTS test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,
    data_strategy VARCHAR(50),
    tags JSONB,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建测试执行记录表
CREATE TABLE IF NOT EXISTS test_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    environment VARCHAR(50),
    status VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms BIGINT,
    result JSONB,
    error_msg TEXT,
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建数据源表
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    url TEXT,
    config JSONB,
    sync_interval VARCHAR(50),
    last_sync_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建AI配置表
CREATE TABLE IF NOT EXISTS ai_settings (
    id SERIAL PRIMARY KEY,
    api_key TEXT NOT NULL,
    model VARCHAR(100) DEFAULT 'gpt-4',
    base_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_scenarios_project_id ON scenarios(project_id);
CREATE INDEX idx_test_cases_scenario_id ON test_cases(scenario_id);
CREATE INDEX idx_test_executions_test_case_id ON test_executions(test_case_id);
CREATE INDEX idx_data_sources_project_id ON data_sources(project_id);

-- 插入默认项目
INSERT INTO projects (name, description) VALUES 
('示例项目', '这是一个示例项目，用于演示AI智能接口测试平台的功能');

COMMENT ON TABLE projects IS '项目表';
COMMENT ON TABLE scenarios IS '测试场景表';
COMMENT ON TABLE test_cases IS '测试用例表';
COMMENT ON TABLE test_executions IS '测试执行记录表';
COMMENT ON TABLE data_sources IS '数据源表';
COMMENT ON TABLE ai_settings IS 'AI配置表';

-- 测试结果表
CREATE TABLE IF NOT EXISTS test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    status VARCHAR(50),
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_test_results_scenario_id ON test_results(scenario_id);
CREATE INDEX idx_test_results_status ON test_results(status);
CREATE INDEX idx_test_results_created_at ON test_results(created_at);

-- 新的 AI 配置表（支持多模型和加密）
CREATE TABLE IF NOT EXISTS ai_configs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,           -- 'openai', 'deepseek', 'local'
    api_key TEXT,                            -- API Key（加密存储，本地模型可为空）
    base_url TEXT,                           -- API 基础 URL
    model_name VARCHAR(100),                 -- 模型名称
    embedding_model VARCHAR(100),            -- 嵌入模型名称
    is_active BOOLEAN DEFAULT false,         -- 是否为当前激活配置
    config_type VARCHAR(50) DEFAULT 'llm',   -- 'llm' 或 'embedding'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_ai_configs_provider ON ai_configs(provider);
CREATE INDEX idx_ai_configs_active ON ai_configs(is_active);
CREATE INDEX idx_ai_configs_type ON ai_configs(config_type);

-- 插入默认配置（本地嵌入模型）
INSERT INTO ai_configs (provider, model_name, embedding_model, is_active, config_type)
VALUES ('local', 'sentence-transformers', 'all-MiniLM-L6-v2', true, 'embedding')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE ai_configs IS 'AI模型配置表（支持多模型）';
