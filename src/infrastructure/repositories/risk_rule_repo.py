"""
风控管理 - 风险规则Repository
使用新的表前缀: mh_risk_rules
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from saturn_mousehunter_shared.foundation.ids import make_ulid
from saturn_mousehunter_shared.aop.decorators import measure, read_only_guard
from saturn_mousehunter_shared.log.logger import get_logger
from infrastructure.db.base_dao import AsyncDAO
from domain.models.risk_rule import (
    RiskRuleIn, RiskRuleOut,
    RiskRuleUpdate, RiskRuleQuery
)

log = get_logger(__name__)

# 使用新的表前缀
TABLE = "mh_risk_rules"


class RiskRuleRepo:
    """风险规则Repository"""

    def __init__(self, dao: AsyncDAO):
        self.dao = dao

    @measure("db_risk_rule_create_seconds")
    async def create(self, rule_data: RiskRuleIn) -> RiskRuleOut:
        """创建风险规则"""
        rule_id = make_ulid()
        now = datetime.now()

        query = f"""
        INSERT INTO {TABLE} (
            id, rule_name, rule_type, description, rule_config,
            threshold_value, warning_threshold, scope, target_ids,
            trigger_conditions, time_window, consecutive_violations,
            actions, action_params, priority, is_enabled,
            effective_from, effective_to, is_active, violation_count,
            created_by, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
            $11, $12, $13, $14, $15, $16, $17, $18, $19,
            $20, $21, $22, $23
        ) RETURNING *
        """

        row = await self.dao.fetch_one(
            query,
            rule_id,
            rule_data.rule_name,
            rule_data.rule_type,
            rule_data.description,
            rule_data.rule_config,
            rule_data.threshold_value,
            rule_data.warning_threshold,
            rule_data.scope,
            rule_data.target_ids,
            rule_data.trigger_conditions,
            rule_data.time_window,
            rule_data.consecutive_violations,
            rule_data.actions,
            rule_data.action_params,
            rule_data.priority,
            rule_data.is_enabled,
            rule_data.effective_from,
            rule_data.effective_to,
            rule_data.is_active,
            0,  # violation_count初始为0
            rule_data.created_by,
            now,
            now
        )

        log.info(f"Created risk rule: {rule_data.rule_name}")
        return RiskRuleOut.from_dict(dict(row))

    @read_only_guard()
    @measure("db_risk_rule_get_seconds")
    async def get_by_id(self, rule_id: str) -> Optional[RiskRuleOut]:
        """根据ID获取风险规则"""
        query = f"SELECT * FROM {TABLE} WHERE id = $1"
        row = await self.dao.fetch_one(query, rule_id)

        if row:
            return RiskRuleOut.from_dict(dict(row))
        return None

    @read_only_guard()
    @measure("db_risk_rule_get_by_name_seconds")
    async def get_by_name(self, rule_name: str) -> Optional[RiskRuleOut]:
        """根据规则名称获取风险规则"""
        query = f"SELECT * FROM {TABLE} WHERE rule_name = $1"
        row = await self.dao.fetch_one(query, rule_name)

        if row:
            return RiskRuleOut.from_dict(dict(row))
        return None

    @measure("db_risk_rule_update_seconds")
    async def update(self, rule_id: str, update_data: RiskRuleUpdate) -> Optional[RiskRuleOut]:
        """更新风险规则"""
        set_clauses = []
        params = []
        param_count = 1

        # 动态构建UPDATE语句
        for field, value in update_data.dict(exclude_unset=True).items():
            if field != 'updated_at':
                set_clauses.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1

        if not set_clauses:
            return await self.get_by_id(rule_id)

        # 添加更新时间
        set_clauses.append(f"updated_at = ${param_count}")
        params.append(datetime.now())
        param_count += 1

        # 添加WHERE条件
        params.append(rule_id)

        query = f"""
        UPDATE {TABLE}
        SET {', '.join(set_clauses)}
        WHERE id = ${param_count}
        RETURNING *
        """

        row = await self.dao.fetch_one(query, *params)
        if row:
            log.info(f"Updated risk rule: {rule_id}")
            return RiskRuleOut.from_dict(dict(row))
        return None

    @measure("db_risk_rule_delete_seconds")
    async def delete(self, rule_id: str) -> bool:
        """删除风险规则（软删除）"""
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

    @read_only_guard()
    @measure("db_risk_rule_get_active_rules_seconds")
    async def get_active_rules(self, rule_type: Optional[str] = None, scope: Optional[str] = None) -> List[RiskRuleOut]:
        """获取生效中的风险规则"""
        conditions = [
            "is_active = true",
            "is_enabled = true",
            "(effective_from IS NULL OR effective_from <= NOW())",
            "(effective_to IS NULL OR effective_to > NOW())"
        ]
        params = []
        param_count = 1

        if rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(rule_type)
            param_count += 1

        if scope:
            conditions.append(f"scope = ${param_count}")
            params.append(scope)
            param_count += 1

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        ORDER BY priority ASC, created_at ASC
        """

        rows = await self.dao.fetch_all(query, *params)
        return [RiskRuleOut.from_dict(dict(row)) for row in rows]

    @read_only_guard()
    @measure("db_risk_rule_get_by_target_seconds")
    async def get_rules_by_target(self, target_id: str, rule_type: Optional[str] = None) -> List[RiskRuleOut]:
        """根据目标ID获取风险规则"""
        conditions = [
            "is_active = true",
            "is_enabled = true",
            "(effective_from IS NULL OR effective_from <= NOW())",
            "(effective_to IS NULL OR effective_to > NOW())",
            f"($1 = ANY(target_ids) OR target_ids IS NULL OR array_length(target_ids, 1) = 0)"
        ]
        params = [target_id]
        param_count = 2

        if rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(rule_type)
            param_count += 1

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        ORDER BY priority ASC, created_at ASC
        """

        rows = await self.dao.fetch_all(query, *params)
        return [RiskRuleOut.from_dict(dict(row)) for row in rows]

    @measure("db_risk_rule_increment_violation_seconds")
    async def increment_violation_count(self, rule_id: str) -> bool:
        """增加违规次数"""
        query = f"""
        UPDATE {TABLE}
        SET violation_count = violation_count + 1,
            last_triggered_at = $1,
            updated_at = $1
        WHERE id = $2
        """

        now = datetime.now()
        result = await self.dao.execute(query, now, rule_id)
        return result > 0

    @measure("db_risk_rule_approve_seconds")
    async def approve(self, rule_id: str, approved_by: str) -> Optional[RiskRuleOut]:
        """审批风险规则"""
        query = f"""
        UPDATE {TABLE}
        SET approved_by = $1,
            approved_at = $2,
            is_enabled = true,
            updated_at = $2
        WHERE id = $3
        RETURNING *
        """

        now = datetime.now()
        row = await self.dao.fetch_one(query, approved_by, now, rule_id)

        if row:
            log.info(f"Approved risk rule: {rule_id}")
            return RiskRuleOut.from_dict(dict(row))
        return None

    @read_only_guard()
    @measure("db_risk_rule_list_seconds")
    async def list(self, query_params: RiskRuleQuery) -> List[RiskRuleOut]:
        """获取风险规则列表"""
        conditions = ["1=1"]
        params = []
        param_count = 1

        # 构建WHERE条件
        if query_params.is_active is not None:
            conditions.append(f"is_active = ${param_count}")
            params.append(query_params.is_active)
            param_count += 1

        if query_params.is_enabled is not None:
            conditions.append(f"is_enabled = ${param_count}")
            params.append(query_params.is_enabled)
            param_count += 1

        if query_params.rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(query_params.rule_type)
            param_count += 1

        if query_params.scope:
            conditions.append(f"scope = ${param_count}")
            params.append(query_params.scope)
            param_count += 1

        if query_params.rule_name:
            conditions.append(f"rule_name ILIKE ${param_count}")
            params.append(f"%{query_params.rule_name}%")
            param_count += 1

        # 构建查询
        base_query = f"""
        SELECT * FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        ORDER BY priority ASC, violation_count DESC, created_at DESC
        """

        # 添加分页
        if query_params.limit:
            base_query += f" LIMIT ${param_count}"
            params.append(query_params.limit)
            param_count += 1

        if query_params.offset:
            base_query += f" OFFSET ${param_count}"
            params.append(query_params.offset)

        rows = await self.dao.fetch_all(base_query, *params)
        return [RiskRuleOut.from_dict(dict(row)) for row in rows]

    @read_only_guard()
    @measure("db_risk_rule_count_seconds")
    async def count(self, query_params: RiskRuleQuery) -> int:
        """获取风险规则总数"""
        conditions = ["1=1"]
        params = []
        param_count = 1

        # 构建WHERE条件 (复用list方法的逻辑)
        if query_params.is_active is not None:
            conditions.append(f"is_active = ${param_count}")
            params.append(query_params.is_active)
            param_count += 1

        if query_params.is_enabled is not None:
            conditions.append(f"is_enabled = ${param_count}")
            params.append(query_params.is_enabled)
            param_count += 1

        if query_params.rule_type:
            conditions.append(f"rule_type = ${param_count}")
            params.append(query_params.rule_type)
            param_count += 1

        if query_params.scope:
            conditions.append(f"scope = ${param_count}")
            params.append(query_params.scope)
            param_count += 1

        query = f"""
        SELECT COUNT(*) as total FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        """

        row = await self.dao.fetch_one(query, *params)
        return row['total'] if row else 0