"""
Risk Rules API Routes
风控规则API路由
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.middleware.auth import get_current_user, get_current_active_user, require_risk_manager
from infrastructure.repositories.risk_rules_repo import RiskRulesRepository
from saturn_mousehunter_shared.log.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/risk/rules", tags=["risk-rules"])


# Pydantic Models
class RiskRuleCreate(BaseModel):
    """创建风控规则请求"""
    rule_name: str = Field(..., min_length=1, max_length=255)
    rule_type: str = Field(..., regex=r'^(POSITION_LIMIT|LOSS_LIMIT|VOLUME_LIMIT|SECTOR_LIMIT|CORRELATION_LIMIT)$')
    category: str = Field(default='GENERAL', regex=r'^(GENERAL|STRATEGY_SPECIFIC|ACCOUNT_SPECIFIC)$')
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    severity: str = Field(default='MEDIUM', regex=r'^(LOW|MEDIUM|HIGH|CRITICAL)$')
    action_type: str = Field(default='ALERT', regex=r'^(ALERT|BLOCK|REDUCE|LIQUIDATE)$')
    priority: int = Field(default=100, ge=1, le=1000)


class RiskRuleResponse(BaseModel):
    """风控规则响应"""
    id: str
    rule_name: str
    rule_type: str
    category: str
    description: Optional[str]
    parameters: Dict[str, Any]
    severity: str
    action_type: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: Optional[str]


class RiskRuleUpdate(BaseModel):
    """更新风控规则"""
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    severity: Optional[str] = Field(None, regex=r'^(LOW|MEDIUM|HIGH|CRITICAL)$')
    action_type: Optional[str] = Field(None, regex=r'^(ALERT|BLOCK|REDUCE|LIQUIDATE)$')
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None


def get_risk_rules_repo() -> RiskRulesRepository:
    """获取风控规则Repository的依赖注入函数"""
    # 这里需要实现依赖注入逻辑
    # 暂时先返回None，实际使用时需要配置
    from infrastructure.config.app_config import get_app_config
    from infrastructure.db.base_dao import AsyncDAO

    config = get_app_config()
    dao = AsyncDAO(config.database_url)
    return RiskRulesRepository(dao)


@router.post("/", response_model=RiskRuleResponse)
async def create_risk_rule(
    rule_data: RiskRuleCreate,
    current_user: dict = Depends(require_risk_manager),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """创建风控规则"""
    try:
        # 检查规则名称是否已存在
        existing_rule = await rules_repo.get_by_name(rule_data.rule_name)
        if existing_rule:
            raise HTTPException(status_code=400, detail="规则名称已存在")

        rule_dict = await rules_repo.create_rule(
            rule_name=rule_data.rule_name,
            rule_type=rule_data.rule_type,
            parameters=rule_data.parameters,
            category=rule_data.category,
            description=rule_data.description,
            severity=rule_data.severity,
            action_type=rule_data.action_type,
            priority=rule_data.priority,
            created_by=current_user.get("username", "unknown")
        )

        return RiskRuleResponse(**rule_dict)

    except Exception as e:
        log.error(f"Error creating risk rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{rule_id}", response_model=RiskRuleResponse)
async def get_risk_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_active_user),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """获取风控规则详情"""
    rule_dict = await rules_repo.get_by_id(rule_id)

    if not rule_dict:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    return RiskRuleResponse(**rule_dict)


@router.get("/", response_model=List[RiskRuleResponse])
async def list_risk_rules(
    rule_type: Optional[str] = Query(None, description="规则类型筛选"),
    category: Optional[str] = Query(None, description="规则分类筛选"),
    severity: Optional[str] = Query(None, description="严重程度筛选"),
    is_active: Optional[bool] = Query(None, description="激活状态筛选"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: dict = Depends(get_current_active_user),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """获取风控规则列表"""
    rules = await rules_repo.list_rules(
        rule_type=rule_type,
        category=category,
        severity=severity,
        is_active=is_active,
        limit=limit,
        offset=offset
    )

    return [RiskRuleResponse(**rule) for rule in rules]


@router.put("/{rule_id}", response_model=RiskRuleResponse)
async def update_risk_rule(
    rule_id: str,
    update_data: RiskRuleUpdate,
    current_user: dict = Depends(require_risk_manager),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """更新风控规则"""
    # 检查规则是否存在
    existing_rule = await rules_repo.get_by_id(rule_id)
    if not existing_rule:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    # 准备更新数据
    updates = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            updates[field] = value

    if not updates:
        return RiskRuleResponse(**existing_rule)

    updated_rule = await rules_repo.update_rule(
        rule_id=rule_id,
        updates=updates,
        updated_by=current_user.get("username", "unknown")
    )

    if not updated_rule:
        raise HTTPException(status_code=400, detail="更新规则失败")

    return RiskRuleResponse(**updated_rule)


@router.delete("/{rule_id}", response_model=dict)
async def delete_risk_rule(
    rule_id: str,
    current_user: dict = Depends(require_risk_manager),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """删除风控规则"""
    success = await rules_repo.delete_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    return {"message": "风控规则删除成功", "rule_id": rule_id}


@router.post("/{rule_id}/activate", response_model=dict)
async def activate_risk_rule(
    rule_id: str,
    current_user: dict = Depends(require_risk_manager),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """激活风控规则"""
    success = await rules_repo.activate_rule(
        rule_id=rule_id,
        updated_by=current_user.get("username", "unknown")
    )

    if not success:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    return {"message": "风控规则激活成功", "rule_id": rule_id}


@router.post("/{rule_id}/deactivate", response_model=dict)
async def deactivate_risk_rule(
    rule_id: str,
    current_user: dict = Depends(require_risk_manager),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """停用风控规则"""
    success = await rules_repo.deactivate_rule(
        rule_id=rule_id,
        updated_by=current_user.get("username", "unknown")
    )

    if not success:
        raise HTTPException(status_code=404, detail="风控规则不存在")

    return {"message": "风控规则停用成功", "rule_id": rule_id}


@router.get("/types/{rule_type}/active", response_model=List[RiskRuleResponse])
async def get_active_rules_by_type(
    rule_type: str,
    current_user: dict = Depends(get_current_active_user),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """获取指定类型的激活规则"""
    rules = await rules_repo.get_active_rules_by_type(rule_type)
    return [RiskRuleResponse(**rule) for rule in rules]


@router.get("/priority/{min_priority}/{max_priority}", response_model=List[RiskRuleResponse])
async def get_rules_by_priority(
    min_priority: int = 0,
    max_priority: int = 1000,
    current_user: dict = Depends(get_current_active_user),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """根据优先级范围获取规则"""
    rules = await rules_repo.get_rules_by_priority(min_priority, max_priority)
    return [RiskRuleResponse(**rule) for rule in rules]


@router.get("/stats/count", response_model=dict)
async def get_rules_statistics(
    rule_type: Optional[str] = Query(None, description="规则类型"),
    category: Optional[str] = Query(None, description="规则分类"),
    current_user: dict = Depends(get_current_active_user),
    rules_repo: RiskRulesRepository = Depends(get_risk_rules_repo)
):
    """获取规则统计信息"""
    total_count = await rules_repo.count_rules(rule_type=rule_type, category=category)
    active_count = await rules_repo.count_rules(rule_type=rule_type, category=category, is_active=True)
    inactive_count = total_count - active_count

    return {
        "total_rules": total_count,
        "active_rules": active_count,
        "inactive_rules": inactive_count,
        "rule_type": rule_type,
        "category": category
    }