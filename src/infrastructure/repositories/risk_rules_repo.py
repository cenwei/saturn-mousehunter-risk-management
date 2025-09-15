"""
Risk Rules Repository
风控规则数据访问层
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from infrastructure.db.base_dao import AsyncDAO
from saturn_mousehunter_shared.log.logger import get_logger
from saturn_mousehunter_shared.aop.decorators import measure

log = get_logger(__name__)

TABLE = "mh_risk_rules"


class RiskRulesRepository:
    """风控规则仓储"""

    def __init__(self, dao: AsyncDAO):
        self.dao = dao

    @measure("db_risk_rules_create_seconds")
    async def create_rule(
        self,
        rule_name: str,
        rule_type: str,
        parameters: Dict[str, Any],
        category: str = 'GENERAL',
        description: Optional[str] = None,
        severity: str = 'MEDIUM',
        action_type: str = 'ALERT',
        priority: int = 100,
        created_by: str = 'system'
    ) -> Dict[str, Any]:
        """创建风控规则"""
        rule_id = str(uuid.uuid4())

        query = f"""
        INSERT INTO {TABLE} (
            id, rule_name, rule_type, category, description, parameters,
            severity, action_type, priority, is_active, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
        """

        result = await self.dao.fetch_one(
            query,
            rule_id,
            rule_name,
            rule_type,
            category,
            description,
            parameters,
            severity,
            action_type,
            priority,
            True,
            created_by
        )

        log.info(f"Created risk rule: {rule_id}")
        return dict(result) if result else {}

    async def get_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取风控规则"""
        query = f"SELECT * FROM {TABLE} WHERE id = $1"
        result = await self.dao.fetch_one(query, rule_id)
        return dict(result) if result else None

    async def get_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取风控规则"""
        query = f"SELECT * FROM {TABLE} WHERE rule_name = $1"
        result = await self.dao.fetch_one(query, rule_name)
        return dict(result) if result else None

    async def list_rules(
        self,
        rule_type: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取风控规则列表"""
        conditions = []
        params = []
        param_count = 1

        if rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(rule_type)
            param_count += 1

        if category:
            conditions.append(f"category = ${param_count}")
            params.append(category)
            param_count += 1

        if severity:
            conditions.append(f"severity = ${param_count}")
            params.append(severity)
            param_count += 1

        if is_active is not None:
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)
            param_count += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {where_clause}
        ORDER BY priority ASC, created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])

        results = await self.dao.fetch_all(query, *params)
        return [dict(row) for row in results]

    async def update_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
        updated_by: str = 'system'
    ) -> Optional[Dict[str, Any]]:
        """更新风控规则"""
        set_clauses = []
        params = []
        param_count = 1

        for field, value in updates.items():
            if field not in ['id', 'created_at', 'updated_at']:
                set_clauses.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1

        if not set_clauses:
            return await self.get_by_id(rule_id)

        # 添加更新者和更新时间
        set_clauses.extend([
            f"updated_by = ${param_count}",
            f"updated_at = ${param_count + 1}"
        ])
        params.extend([updated_by, datetime.now()])
        param_count += 2

        # 添加WHERE条件
        params.append(rule_id)

        query = f"""
        UPDATE {TABLE}
        SET {', '.join(set_clauses)}
        WHERE id = ${param_count}
        RETURNING *
        """

        result = await self.dao.fetch_one(query, *params)
        if result:
            log.info(f"Updated risk rule: {rule_id}")
        return dict(result) if result else None

    async def delete_rule(self, rule_id: str) -> bool:
        """删除风控规则（软删除）"""
        query = f"""
        UPDATE {TABLE}
        SET is_active = false, updated_at = $1
        WHERE id = $2
        """

        result = await self.dao.execute(query, datetime.now(), rule_id)
        success = result > 0
        if success:
            log.info(f"Deleted risk rule: {rule_id}")
        return success

    async def activate_rule(self, rule_id: str, updated_by: str = 'system') -> bool:
        """激活风控规则"""
        query = f"""
        UPDATE {TABLE}
        SET is_active = true, updated_by = $2, updated_at = $3
        WHERE id = $1
        """

        result = await self.dao.execute(query, rule_id, updated_by, datetime.now())
        success = result > 0
        if success:
            log.info(f"Activated risk rule: {rule_id}")
        return success

    async def deactivate_rule(self, rule_id: str, updated_by: str = 'system') -> bool:
        """停用风控规则"""
        query = f"""
        UPDATE {TABLE}
        SET is_active = false, updated_by = $2, updated_at = $3
        WHERE id = $1
        """

        result = await self.dao.execute(query, rule_id, updated_by, datetime.now())
        success = result > 0
        if success:
            log.info(f"Deactivated risk rule: {rule_id}")
        return success

    async def get_active_rules_by_type(self, rule_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的活跃规则"""
        query = f"""
        SELECT * FROM {TABLE}
        WHERE rule_type = $1 AND is_active = true
        ORDER BY priority ASC
        """

        results = await self.dao.fetch_all(query, rule_type)
        return [dict(row) for row in results]

    async def get_rules_by_priority(self, min_priority: int = 0, max_priority: int = 1000) -> List[Dict[str, Any]]:
        """根据优先级范围获取规则"""
        query = f"""
        SELECT * FROM {TABLE}
        WHERE priority >= $1 AND priority <= $2 AND is_active = true
        ORDER BY priority ASC, created_at DESC
        """

        results = await self.dao.fetch_all(query, min_priority, max_priority)
        return [dict(row) for row in results]

    async def count_rules(
        self,
        rule_type: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """统计风控规则数量"""
        conditions = []
        params = []
        param_count = 1

        if rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(rule_type)
            param_count += 1

        if category:
            conditions.append(f"category = ${param_count}")
            params.append(category)
            param_count += 1

        if is_active is not None:
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)
            param_count += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT COUNT(*) as total FROM {TABLE}
        WHERE {where_clause}
        """

        result = await self.dao.fetch_one(query, *params)
        return result['total'] if result else 0