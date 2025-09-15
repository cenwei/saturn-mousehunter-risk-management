"""
Risk Events API Routes
风控事件API路由
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.middleware.auth import get_current_user, get_current_active_user, require_risk_manager
from infrastructure.repositories.risk_events_repo import RiskEventsRepository
from saturn_mousehunter_shared.log.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/risk/events", tags=["risk-events"])


# Pydantic Models
class RiskEventCreate(BaseModel):
    """创建风控事件请求"""
    event_type: str = Field(..., regex=r'^(RULE_VIOLATION|THRESHOLD_BREACH|ANOMALY_DETECTED|MANUAL_INTERVENTION)$')
    severity: str = Field(..., regex=r'^(LOW|MEDIUM|HIGH|CRITICAL)$')
    source_type: str = Field(..., regex=r'^(RULE|MONITOR|MANUAL|SYSTEM)$')
    target_type: str = Field(..., regex=r'^(ACCOUNT|STRATEGY|POSITION|ORDER)$')
    target_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_id: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    risk_metrics: Optional[Dict[str, Any]] = None
    action_taken: str = Field(default='NONE', regex=r'^(NONE|ALERT|BLOCK|REDUCE|LIQUIDATE)$')


class RiskEventResponse(BaseModel):
    """风控事件响应"""
    id: str
    event_type: str
    severity: str
    source_type: str
    source_id: Optional[str]
    target_type: str
    target_id: str
    title: str
    description: Optional[str]
    event_data: Optional[Dict[str, Any]]
    risk_metrics: Optional[Dict[str, Any]]
    action_taken: str
    status: str
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    resolution_note: Optional[str]
    created_at: datetime
    updated_at: datetime


class EventStatusUpdate(BaseModel):
    """事件状态更新"""
    status: str = Field(..., regex=r'^(OPEN|ACKNOWLEDGED|RESOLVED|IGNORED)$')
    resolution_note: Optional[str] = None


def get_risk_events_repo() -> RiskEventsRepository:
    """获取风控事件Repository的依赖注入函数"""
    from infrastructure.config.app_config import get_app_config
    from infrastructure.db.base_dao import AsyncDAO

    config = get_app_config()
    dao = AsyncDAO(config.database_url)
    return RiskEventsRepository(dao)


@router.post("/", response_model=RiskEventResponse)
async def create_risk_event(
    event_data: RiskEventCreate,
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """创建风控事件"""
    try:
        event_dict = await events_repo.create_event(
            event_type=event_data.event_type,
            severity=event_data.severity,
            source_type=event_data.source_type,
            target_type=event_data.target_type,
            target_id=event_data.target_id,
            title=event_data.title,
            description=event_data.description,
            source_id=event_data.source_id,
            event_data=event_data.event_data,
            risk_metrics=event_data.risk_metrics,
            action_taken=event_data.action_taken
        )

        return RiskEventResponse(**event_dict)

    except Exception as e:
        log.error(f"Error creating risk event: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{event_id}", response_model=RiskEventResponse)
async def get_risk_event(
    event_id: str,
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取风控事件详情"""
    event_dict = await events_repo.get_by_id(event_id)

    if not event_dict:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    return RiskEventResponse(**event_dict)


@router.get("/", response_model=List[RiskEventResponse])
async def list_risk_events(
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    severity: Optional[str] = Query(None, description="严重程度筛选"),
    source_type: Optional[str] = Query(None, description="来源类型筛选"),
    target_type: Optional[str] = Query(None, description="目标类型筛选"),
    target_id: Optional[str] = Query(None, description="目标ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取风控事件列表"""
    events = await events_repo.list_events(
        event_type=event_type,
        severity=severity,
        source_type=source_type,
        target_type=target_type,
        target_id=target_id,
        status=status,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )

    return [RiskEventResponse(**event) for event in events]


@router.put("/{event_id}/status", response_model=dict)
async def update_event_status(
    event_id: str,
    status_update: EventStatusUpdate,
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """更新事件状态"""
    success = await events_repo.update_event_status(
        event_id=event_id,
        status=status_update.status,
        resolved_by=current_user.get("username", "unknown"),
        resolution_note=status_update.resolution_note
    )

    if not success:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    return {
        "message": "事件状态更新成功",
        "event_id": event_id,
        "new_status": status_update.status
    }


@router.post("/{event_id}/acknowledge", response_model=dict)
async def acknowledge_event(
    event_id: str,
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """确认事件"""
    success = await events_repo.acknowledge_event(
        event_id=event_id,
        acknowledged_by=current_user.get("username", "unknown")
    )

    if not success:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    return {
        "message": "事件确认成功",
        "event_id": event_id,
        "acknowledged_by": current_user.get("username")
    }


@router.post("/{event_id}/resolve", response_model=dict)
async def resolve_event(
    event_id: str,
    resolution_note: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """解决事件"""
    success = await events_repo.resolve_event(
        event_id=event_id,
        resolved_by=current_user.get("username", "unknown"),
        resolution_note=resolution_note
    )

    if not success:
        raise HTTPException(status_code=404, detail="风控事件不存在")

    return {
        "message": "事件解决成功",
        "event_id": event_id,
        "resolved_by": current_user.get("username")
    }


@router.get("/stats/open-count", response_model=dict)
async def get_open_events_count(
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取未处理事件数量"""
    count = await events_repo.get_open_events_count()
    return {"open_events_count": count}


@router.get("/critical/list", response_model=List[RiskEventResponse])
async def get_critical_events(
    limit: int = Query(20, le=100, description="返回数量限制"),
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取严重事件列表"""
    events = await events_repo.get_critical_events(limit=limit)
    return [RiskEventResponse(**event) for event in events]


@router.get("/target/{target_type}/{target_id}", response_model=List[RiskEventResponse])
async def get_events_by_target(
    target_type: str,
    target_id: str,
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取特定目标的事件"""
    events = await events_repo.get_events_by_target(
        target_type=target_type,
        target_id=target_id,
        status=status,
        limit=limit
    )

    return [RiskEventResponse(**event) for event in events]


@router.get("/stats/summary", response_model=dict)
async def get_events_statistics(
    start_date: Optional[datetime] = Query(None, description="统计开始日期"),
    end_date: Optional[datetime] = Query(None, description="统计结束日期"),
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取事件统计信息"""
    stats = await events_repo.get_events_statistics(
        start_date=start_date,
        end_date=end_date
    )
    return stats


@router.get("/recent/list", response_model=List[RiskEventResponse])
async def get_recent_events(
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    severity: Optional[str] = Query(None, description="严重程度筛选"),
    limit: int = Query(100, le=500, description="返回数量限制"),
    current_user: dict = Depends(get_current_active_user),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """获取最近的事件"""
    events = await events_repo.get_recent_events(
        hours=hours,
        severity=severity,
        limit=limit
    )

    return [RiskEventResponse(**event) for event in events]


@router.delete("/maintenance/cleanup", response_model=dict)
async def cleanup_old_events(
    days_old: int = Query(90, ge=30, description="清理天数"),
    current_user: dict = Depends(require_risk_manager),
    events_repo: RiskEventsRepository = Depends(get_risk_events_repo)
):
    """清理旧事件数据（管理员权限）"""
    deleted_count = await events_repo.delete_old_events(days_old=days_old)

    return {
        "message": f"清理了 {deleted_count} 条旧事件记录",
        "deleted_count": deleted_count
    }