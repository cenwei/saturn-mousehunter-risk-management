"""
Risk Management Application Configuration
风控管理应用配置
"""
import os
from functools import lru_cache
from typing import Optional, List

from pydantic import BaseSettings, Field


class AppConfig(BaseSettings):
    """风控管理应用配置"""

    # 应用信息
    app_name: str = "Saturn MouseHunter Risk Management"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="RISK_ENVIRONMENT")
    debug: bool = Field(default=False, env="RISK_DEBUG")

    # 服务配置
    host: str = Field(default="0.0.0.0", env="RISK_HOST")
    port: int = Field(default=8003, env="RISK_PORT")

    # 数据库配置
    database_url: str = Field(..., env="RISK_DATABASE_URL")

    # JWT配置（从认证服务获取）
    jwt_secret_key: str = Field(..., env="RISK_JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="RISK_JWT_ALGORITHM")

    # 日志配置
    log_level: str = Field(default="INFO", env="RISK_LOG_LEVEL")
    log_format: str = Field(default="json", env="RISK_LOG_FORMAT")

    # CORS配置
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://192.168.8.168:3000"],
        env="RISK_CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="RISK_CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="RISK_CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="RISK_CORS_ALLOW_HEADERS")

    # Redis配置（可选，用于缓存和消息队列）
    redis_url: Optional[str] = Field(None, env="RISK_REDIS_URL")

    # 风控业务配置
    max_position_limit: float = Field(default=1000000.0, env="RISK_MAX_POSITION_LIMIT")
    max_daily_loss_limit: float = Field(default=50000.0, env="RISK_MAX_DAILY_LOSS_LIMIT")
    max_drawdown_limit: float = Field(default=0.1, env="RISK_MAX_DRAWDOWN_LIMIT")  # 10%
    var_confidence_level: float = Field(default=0.95, env="RISK_VAR_CONFIDENCE_LEVEL")

    # 监控配置
    real_time_check_interval: int = Field(default=60, env="RISK_REAL_TIME_CHECK_INTERVAL")  # 秒
    intraday_check_interval: int = Field(default=300, env="RISK_INTRADAY_CHECK_INTERVAL")  # 秒
    eod_check_time: str = Field(default="16:00", env="RISK_EOD_CHECK_TIME")

    # 通知配置
    alert_email_enabled: bool = Field(default=True, env="RISK_ALERT_EMAIL_ENABLED")
    alert_sms_enabled: bool = Field(default=False, env="RISK_ALERT_SMS_ENABLED")
    alert_webhook_url: Optional[str] = Field(None, env="RISK_ALERT_WEBHOOK_URL")

    # 监控配置
    enable_metrics: bool = Field(default=True, env="RISK_ENABLE_METRICS")
    metrics_port: int = Field(default=9003, env="RISK_METRICS_PORT")

    # 外部服务配置
    auth_service_url: str = Field(default="http://192.168.8.168:8001", env="AUTH_SERVICE_URL")
    strategy_service_url: str = Field(default="http://192.168.8.168:8002", env="STRATEGY_SERVICE_URL")
    account_service_url: str = Field(default="http://192.168.8.168:8004", env="ACCOUNT_SERVICE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_app_config() -> AppConfig:
    """获取应用配置（单例）"""
    return AppConfig()