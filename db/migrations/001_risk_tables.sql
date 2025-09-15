-- Risk Management Database Schema
-- Tables with mh_risk_* prefix

-- 风控规则表
CREATE TABLE IF NOT EXISTS mh_risk_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(255) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('POSITION_LIMIT', 'LOSS_LIMIT', 'VOLUME_LIMIT', 'SECTOR_LIMIT', 'CORRELATION_LIMIT')),
    category VARCHAR(50) DEFAULT 'GENERAL', -- GENERAL, STRATEGY_SPECIFIC, ACCOUNT_SPECIFIC
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}', -- 规则参数配置
    severity VARCHAR(20) DEFAULT 'MEDIUM' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    action_type VARCHAR(20) DEFAULT 'ALERT' CHECK (action_type IN ('ALERT', 'BLOCK', 'REDUCE', 'LIQUIDATE')),
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100, -- 规则优先级，数字越小优先级越高
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- 风控监控表
CREATE TABLE IF NOT EXISTS mh_risk_monitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_name VARCHAR(255) NOT NULL,
    monitor_type VARCHAR(50) NOT NULL CHECK (monitor_type IN ('REAL_TIME', 'END_OF_DAY', 'INTRADAY', 'CUSTOM')),
    target_type VARCHAR(50) NOT NULL CHECK (target_type IN ('ACCOUNT', 'STRATEGY', 'PORTFOLIO', 'POSITION')),
    target_id VARCHAR(255), -- 监控目标ID
    rules JSONB NOT NULL DEFAULT '[]', -- 关联的风控规则ID列表
    thresholds JSONB NOT NULL DEFAULT '{}', -- 阈值配置
    notification_config JSONB DEFAULT '{}', -- 通知配置
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    last_check_at TIMESTAMP WITH TIME ZONE,
    next_check_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- 风控事件表
CREATE TABLE IF NOT EXISTS mh_risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('RULE_VIOLATION', 'THRESHOLD_BREACH', 'ANOMALY_DETECTED', 'MANUAL_INTERVENTION')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('RULE', 'MONITOR', 'MANUAL', 'SYSTEM')),
    source_id VARCHAR(255), -- 触发源ID (规则ID或监控ID)
    target_type VARCHAR(50) NOT NULL CHECK (target_type IN ('ACCOUNT', 'STRATEGY', 'POSITION', 'ORDER')),
    target_id VARCHAR(255), -- 目标对象ID
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_data JSONB DEFAULT '{}', -- 事件详细数据
    risk_metrics JSONB DEFAULT '{}', -- 相关风险指标
    action_taken VARCHAR(20) CHECK (action_taken IN ('NONE', 'ALERT', 'BLOCK', 'REDUCE', 'LIQUIDATE')),
    status VARCHAR(20) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'IGNORED')),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255),
    resolution_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 黑白名单表
CREATE TABLE IF NOT EXISTS mh_risk_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_name VARCHAR(255) NOT NULL,
    list_type VARCHAR(20) NOT NULL CHECK (list_type IN ('BLACKLIST', 'WHITELIST', 'WATCHLIST')),
    category VARCHAR(50) NOT NULL CHECK (category IN ('SYMBOL', 'STRATEGY', 'USER', 'IP', 'SECTOR')),
    items JSONB NOT NULL DEFAULT '[]', -- 名单项目列表
    reason TEXT,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_to TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255)
);

-- 风控配置表
CREATE TABLE IF NOT EXISTS mh_risk_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name VARCHAR(255) NOT NULL UNIQUE,
    config_type VARCHAR(50) NOT NULL CHECK (config_type IN ('GLOBAL', 'ACCOUNT', 'STRATEGY', 'PORTFOLIO')),
    scope VARCHAR(255), -- 配置作用范围 (account_id, strategy_id等)
    config_data JSONB NOT NULL DEFAULT '{}', -- 配置数据
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    UNIQUE(config_name, scope)
);

-- 风控指标表
CREATE TABLE IF NOT EXISTS mh_risk_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('VAR', 'DRAWDOWN', 'VOLATILITY', 'BETA', 'SHARPE', 'EXPOSURE')),
    target_type VARCHAR(50) NOT NULL CHECK (target_type IN ('ACCOUNT', 'STRATEGY', 'PORTFOLIO', 'POSITION')),
    target_id VARCHAR(255) NOT NULL,
    metric_value DECIMAL(15,6),
    threshold_value DECIMAL(15,6),
    status VARCHAR(20) DEFAULT 'NORMAL' CHECK (status IN ('NORMAL', 'WARNING', 'CRITICAL')),
    calculation_params JSONB DEFAULT '{}',
    calculation_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_risk_metrics_target (target_type, target_id),
    INDEX idx_risk_metrics_time (calculation_time),
    INDEX idx_risk_metrics_status (status)
);

-- 风控日志表
CREATE TABLE IF NOT EXISTS mh_risk_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_type VARCHAR(50) NOT NULL CHECK (log_type IN ('RULE_CHECK', 'MONITOR_RUN', 'EVENT_TRIGGER', 'ACTION_TAKEN', 'CONFIG_CHANGE')),
    operation VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    user_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    result VARCHAR(20) CHECK (result IN ('SUCCESS', 'FAILURE', 'PARTIAL')),
    execution_time INTEGER, -- 执行时间(毫秒)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_risk_logs_type (log_type),
    INDEX idx_risk_logs_time (created_at),
    INDEX idx_risk_logs_user (user_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_risk_rules_type ON mh_risk_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_risk_rules_active ON mh_risk_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_risk_monitors_type ON mh_risk_monitors(monitor_type, target_type);
CREATE INDEX IF NOT EXISTS idx_risk_monitors_status ON mh_risk_monitors(status);
CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON mh_risk_events(severity);
CREATE INDEX IF NOT EXISTS idx_risk_events_status ON mh_risk_events(status);
CREATE INDEX IF NOT EXISTS idx_risk_events_time ON mh_risk_events(created_at);
CREATE INDEX IF NOT EXISTS idx_risk_events_target ON mh_risk_events(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_risk_lists_type ON mh_risk_lists(list_type, category);
CREATE INDEX IF NOT EXISTS idx_risk_lists_active ON mh_risk_lists(is_active);
CREATE INDEX IF NOT EXISTS idx_risk_configs_type ON mh_risk_configs(config_type);
CREATE INDEX IF NOT EXISTS idx_risk_configs_active ON mh_risk_configs(is_active);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_risk_rules_updated_at
    BEFORE UPDATE ON mh_risk_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_risk_monitors_updated_at
    BEFORE UPDATE ON mh_risk_monitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_risk_events_updated_at
    BEFORE UPDATE ON mh_risk_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_risk_lists_updated_at
    BEFORE UPDATE ON mh_risk_lists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_risk_configs_updated_at
    BEFORE UPDATE ON mh_risk_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();