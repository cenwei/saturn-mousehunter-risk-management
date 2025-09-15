"""
风控管理服务简化测试版本
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid


class RiskRuleIn(BaseModel):
    rule_name: str
    rule_type: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = {}
    severity: str = "MEDIUM"
    action_type: str = "ALERT"
    priority: int = 100



class RiskRuleOut(BaseModel):
    id: str
    rule_name: str
    rule_type: str
    description: Optional[str]
    parameters: Dict[str, Any]
    severity: str
    action_type: str
    priority: int
    is_active: bool = True
    created_at: datetime


class RiskEventIn(BaseModel):
    event_type: str
    severity: str
    source_type: str
    target_type: str
    target_id: str
    title: str
    description: Optional[str] = None


class RiskEventOut(BaseModel):
    id: str
    event_type: str
    severity: str
    source_type: str
    target_type: str
    target_id: str
    title: str
    description: Optional[str]
    status: str = "OPEN"
    created_at: datetime


# 简化的内存存储
rules_db = {}
events_db = {}
rule_counter = 1
event_counter = 1

app = FastAPI(
    title="Saturn MouseHunter Risk Management",
    version="1.0.0",
    description="风控管理服务 - 提供风险监控、规则管理、事件处理功能"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """根路径"""
    return {
        "message": "Saturn MouseHunter Risk Management",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "risk-management",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# 风控规则API
@app.post("/api/v1/risk/rules/", response_model=RiskRuleOut)
def create_risk_rule(rule_data: RiskRuleIn):
    """创建风控规则"""
    global rule_counter

    # 检查规则名称重复
    for rule in rules_db.values():
        if rule.rule_name == rule_data.rule_name:
            raise HTTPException(status_code=400, detail="规则名称已存在")

    rule_id = f"rule_{rule_counter}"
    rule_counter += 1

    new_rule = RiskRuleOut(
        id=rule_id,
        rule_name=rule_data.rule_name,
        rule_type=rule_data.rule_type,
        description=rule_data.description,
        parameters=rule_data.parameters,
        severity=rule_data.severity,
        action_type=rule_data.action_type,
        priority=rule_data.priority,
        created_at=datetime.now(timezone.utc)
    )

    rules_db[rule_id] = new_rule
    return new_rule


@app.get("/api/v1/risk/rules/", response_model=List[RiskRuleOut])
def list_risk_rules(
    rule_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """获取风控规则列表"""
    rules = list(rules_db.values())

    # 过滤条件
    if rule_type:
        rules = [r for r in rules if r.rule_type == rule_type]
    if severity:
        rules = [r for r in rules if r.severity == severity]

    return rules[:limit]


@app.get("/api/v1/risk/rules/{rule_id}", response_model=RiskRuleOut)
def get_risk_rule(rule_id: str):
    """获取风控规则详情"""
    if rule_id not in rules_db:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    return rules_db[rule_id]


# 风控事件API
@app.post("/api/v1/risk/events/", response_model=RiskEventOut)
def create_risk_event(event_data: RiskEventIn):
    """创建风控事件"""
    global event_counter

    event_id = f"event_{event_counter}"
    event_counter += 1

    new_event = RiskEventOut(
        id=event_id,
        event_type=event_data.event_type,
        severity=event_data.severity,
        source_type=event_data.source_type,
        target_type=event_data.target_type,
        target_id=event_data.target_id,
        title=event_data.title,
        description=event_data.description,
        created_at=datetime.now(timezone.utc)
    )

    events_db[event_id] = new_event
    return new_event


@app.get("/api/v1/risk/events/", response_model=List[RiskEventOut])
def list_risk_events(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """获取风控事件列表"""
    events = list(events_db.values())

    # 过滤条件
    if severity:
        events = [e for e in events if e.severity == severity]
    if status:
        events = [e for e in events if e.status == status]

    return events[:limit]


@app.get("/api/v1/risk/events/{event_id}", response_model=RiskEventOut)
def get_risk_event(event_id: str):
    """获取风控事件详情"""
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    return events_db[event_id]


@app.post("/api/v1/risk/events/{event_id}/acknowledge")
def acknowledge_event(event_id: str):
    """确认事件"""
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    events_db[event_id].status = "ACKNOWLEDGED"
    return {"message": "事件确认成功"}


@app.get("/api/v1/risk/events/stats/open-count")
def get_open_events_count():
    """获取未处理事件数量"""
    open_count = sum(1 for e in events_db.values() if e.status == "OPEN")
    return {"open_events_count": open_count}


@app.get("/api/v1/risk/events/critical/list", response_model=List[RiskEventOut])
def get_critical_events(limit: int = 10):
    """获取严重事件列表"""
    critical_events = [e for e in events_db.values() if e.severity == "CRITICAL"]
    return critical_events[:limit]


if __name__ == "__main__":
    import uvicorn
    print("🚀 启动风控管理服务...")
    print("📍 访问地址:")
    print("   - API文档: http://192.168.8.168:8003/docs")
    print("   - 健康检查: http://192.168.8.168:8003/health")
    print("   - 创建风控规则: POST http://192.168.8.168:8003/api/v1/risk/rules/")
    print("   - 创建风控事件: POST http://192.168.8.168:8003/api/v1/risk/events/")

    uvicorn.run(
        "__main__:app",
        host="0.0.0.0",
        port=8003,
        reload=False
    )