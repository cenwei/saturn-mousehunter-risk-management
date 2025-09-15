"""
Risk Events Repository
风控事件数据访问层
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from infrastructure.db.base_dao import AsyncDAO
from saturn_mousehunter_shared.log.logger import get_logger
from saturn_mousehunter_shared.aop.decorators import measure

log = get_logger(__name__)

TABLE = "mh_risk_events"


class RiskEventsRepository:
    """风控事件仓储"""

    def __init__(self, dao: AsyncDAO):
        self.dao = dao

    @measure("db_risk_events_create_seconds")
    async def create_event(
        self,
        event_type: str,
        severity: str,
        source_type: str,
        target_type: str,
        target_id: str,
        title: str,
        description: Optional[str] = None,
        source_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        action_taken: str = 'NONE'
    ) -> Dict[str, Any]:
        """创建风控事件"""
        event_id = str(uuid.uuid4())
        event_data = event_data or {}
        risk_metrics = risk_metrics or {}

        query = f"""
        INSERT INTO {TABLE} (
            id, event_type, severity, source_type, source_id, target_type, target_id,
            title, description, event_data, risk_metrics, action_taken, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING *
        """

        result = await self.dao.fetch_one(
            query,
            event_id,
            event_type,
            severity,
            source_type,
            source_id,
            target_type,
            target_id,
            title,
            description,
            event_data,
            risk_metrics,
            action_taken,
            'OPEN'
        )

        log.info(f"Created risk event: {event_id}")
        return dict(result) if result else {}

    async def get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取风控事件"""
        query = f"SELECT * FROM {TABLE} WHERE id = $1"
        result = await self.dao.fetch_one(query, event_id)
        return dict(result) if result else None

    async def list_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取风控事件列表"""
        conditions = []
        params = []
        param_count = 1

        if event_type:
            conditions.append(f"event_type = ${param_count}")
            params.append(event_type)
            param_count += 1

        if severity:
            conditions.append(f"severity = ${param_count}")
            params.append(severity)
            param_count += 1

        if source_type:
            conditions.append(f"source_type = ${param_count}")
            params.append(source_type)
            param_count += 1

        if target_type:
            conditions.append(f"target_type = ${param_count}")
            params.append(target_type)
            param_count += 1

        if target_id:
            conditions.append(f"target_id = ${param_count}")
            params.append(target_id)
            param_count += 1

        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        if start_time:
            conditions.append(f"created_at >= ${param_count}")
            params.append(start_time)
            param_count += 1

        if end_time:
            conditions.append(f"created_at <= ${param_count}")
            params.append(end_time)
            param_count += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])

        results = await self.dao.fetch_all(query, *params)
        return [dict(row) for row in results]

    async def update_event_status(
        self,
        event_id: str,
        status: str,
        resolved_by: Optional[str] = None,
        resolution_note: Optional[str] = None
    ) -> bool:
        """更新事件状态"""
        resolved_at = datetime.now() if status in ['RESOLVED', 'IGNORED'] else None

        query = f"""
        UPDATE {TABLE}
        SET status = $2, resolved_at = $3, resolved_by = $4,
            resolution_note = $5, updated_at = $6
        WHERE id = $1
        """

        result = await self.dao.execute(
            query, event_id, status, resolved_at, resolved_by, resolution_note, datetime.now()
        )
        success = result > 0
        if success:
            log.info(f"Updated event status: {event_id} -> {status}")
        return success

    async def acknowledge_event(self, event_id: str, acknowledged_by: str) -> bool:
        """确认事件"""
        return await self.update_event_status(event_id, 'ACKNOWLEDGED', acknowledged_by)

    async def resolve_event(
        self,
        event_id: str,
        resolved_by: str,
        resolution_note: Optional[str] = None
    ) -> bool:
        """解决事件"""
        return await self.update_event_status(event_id, 'RESOLVED', resolved_by, resolution_note)

    async def get_open_events_count(self) -> int:
        """获取未处理事件数量"""
        query = f"SELECT COUNT(*) as total FROM {TABLE} WHERE status = 'OPEN'"
        result = await self.dao.fetch_one(query)
        return result['total'] if result else 0

    async def get_critical_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取严重事件列表"""
        query = f"""
        SELECT * FROM {TABLE}
        WHERE severity = 'CRITICAL' AND status IN ('OPEN', 'ACKNOWLEDGED')
        ORDER BY created_at DESC
        LIMIT $1
        """

        results = await self.dao.fetch_all(query, limit)
        return [dict(row) for row in results]

    async def get_events_by_target(
        self,
        target_type: str,
        target_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取特定目标的事件"""
        conditions = ["target_type = $1", "target_id = $2"]
        params = [target_type, target_id]
        param_count = 3

        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT ${param_count}
        """
        params.append(limit)

        results = await self.dao.fetch_all(query, *params)
        return [dict(row) for row in results]

    async def get_events_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取事件统计"""
        conditions = []
        params = []
        param_count = 1

        if start_date:
            conditions.append(f"created_at >= ${param_count}")
            params.append(start_date)
            param_count += 1

        if end_date:
            conditions.append(f"created_at <= ${param_count}")
            params.append(end_date)
            param_count += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
        SELECT
            COUNT(*) as total_events,
            COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_events,
            COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_events,
            COUNT(CASE WHEN severity = 'MEDIUM' THEN 1 END) as medium_events,
            COUNT(CASE WHEN severity = 'LOW' THEN 1 END) as low_events,
            COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as open_events,
            COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved_events,
            COUNT(DISTINCT target_id) as affected_targets
        FROM {TABLE}
        WHERE {where_clause}
        """

        result = await self.dao.fetch_one(query, *params)
        return dict(result) if result else {}

    async def get_recent_events(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取最近的事件"""
        since_time = datetime.now() - timedelta(hours=hours)
        conditions = ["created_at >= $1"]
        params = [since_time]
        param_count = 2

        if severity:
            conditions.append(f"severity = ${param_count}")
            params.append(severity)
            param_count += 1

        query = f"""
        SELECT * FROM {TABLE}
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT ${param_count}
        """
        params.append(limit)

        results = await self.dao.fetch_all(query, *params)
        return [dict(row) for row in results]

    async def delete_old_events(self, days_old: int = 90) -> int:
        """删除旧事件"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        query = f"""
        DELETE FROM {TABLE}
        WHERE created_at < $1 AND status IN ('RESOLVED', 'IGNORED')
        """

        result = await self.dao.execute(query, cutoff_date)
        if result > 0:
            log.info(f"Deleted {result} old risk events")
        return result