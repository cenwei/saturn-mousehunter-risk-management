"""
Risk Alert Models
风险告警模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class RiskAlertIn(BaseModel):
    """风险告警输入模型"""
    alert_name: str = Field(..., description="告警名称")
    alert_type: str = Field(..., description="告警类型")
    severity: str = Field(..., description="严重程度")
    rule_id: str = Field(..., description="触发规则ID")
    target_id: str = Field(..., description="目标ID")
    target_type: str = Field(..., description="目标类型")
    threshold_value: Decimal = Field(..., description="阈值")
    actual_value: Decimal = Field(..., description="实际值")
    description: Optional[str] = Field(None, description="描述")
    alert_data: Dict[str, Any] = Field(default_factory=dict, description="告警数据")
    is_active: bool = Field(default=True, description="是否激活")
    created_by: str = Field(..., description="创建者")

    @validator('alert_type')
    def validate_alert_type(cls, v):
        allowed_types = ['THRESHOLD', 'ANOMALY', 'TREND', 'CORRELATION', 'SYSTEM']
        if v not in allowed_types:
            raise ValueError(f'Alert type must be one of {allowed_types}')
        return v

    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of {allowed_severities}')
        return v

    @validator('target_type')
    def validate_target_type(cls, v):
        allowed_types = ['STRATEGY', 'PORTFOLIO', 'ACCOUNT', 'INSTRUMENT', 'SYSTEM']
        if v not in allowed_types:
            raise ValueError(f'Target type must be one of {allowed_types}')
        return v

    class Config:
        from_attributes = True


class RiskAlertOut(BaseModel):
    """风险告警输出模型"""
    id: str
    alert_name: str
    alert_type: str
    severity: str
    status: str  # ACTIVE, ACKNOWLEDGED, RESOLVED, DISMISSED
    rule_id: str
    target_id: str
    target_type: str
    threshold_value: Decimal
    actual_value: Decimal
    description: Optional[str]
    alert_data: Dict[str, Any]
    is_active: bool

    # 处理信息
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]

    created_by: str
    created_at: datetime
    updated_at: datetime

    # 关联信息
    rule_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "RiskAlertOut":
        """从字典创建实例"""
        return cls(**data)

    class Config:
        from_attributes = True


class RiskAlertUpdate(BaseModel):
    """风险告警更新模型"""
    alert_name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    alert_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of {allowed_statuses}')
        return v

    class Config:
        from_attributes = True


class RiskAlertQuery(BaseModel):
    """风险告警查询模型"""
    alert_name: Optional[str] = None
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    rule_id: Optional[str] = None
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    offset: Optional[int] = Field(None, ge=0)

    class Config:
        from_attributes = True


class RiskAlertStats(BaseModel):
    """风险告警统计模型"""
    total_alerts: int
    active_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int
    dismissed_alerts: int
    alerts_by_type: Dict[str, int]
    alerts_by_severity: Dict[str, int]
    avg_resolution_time: Optional[float]

    class Config:
        from_attributes = True