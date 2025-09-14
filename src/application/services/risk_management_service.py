"""
Risk Management Service
风险管理业务逻辑服务
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from saturn_mousehunter_shared.foundation.ids import make_ulid
from saturn_mousehunter_shared.aop.decorators import measure
from saturn_mousehunter_shared.log.logger import get_logger
from infrastructure.repositories import RiskRuleRepo, RiskAlertRepo
from domain.models import (
    RiskRuleIn, RiskRuleOut, RiskRuleUpdate, RiskRuleQuery,
    RiskAlertIn, RiskAlertOut, RiskAlertUpdate, RiskAlertQuery
)

log = get_logger(__name__)


class RiskManagementService:
    """风险管理服务"""

    def __init__(
        self,
        risk_rule_repo: RiskRuleRepo,
        risk_alert_repo: RiskAlertRepo
    ):
        self.risk_rule_repo = risk_rule_repo
        self.risk_alert_repo = risk_alert_repo

    @measure("risk_management_evaluate_rules_seconds")
    async def evaluate_risk_rules(
        self,
        target_type: str,
        target_id: str,
        data: Dict[str, Any]
    ) -> List[RiskAlertOut]:
        """评估风险规则"""
        # 获取适用的风险规则
        rules = await self.risk_rule_repo.get_rules_by_target(target_id)
        type_rules = await self.risk_rule_repo.get_active_rules(rule_type=target_type)

        all_rules = rules + type_rules
        triggered_alerts = []

        for rule in all_rules:
            try:
                is_triggered = await self._evaluate_single_rule(rule, data)
                if is_triggered:
                    alert = await self._create_alert_from_rule(rule, target_id, target_type, data)
                    triggered_alerts.append(alert)

                    # 增加违规计数
                    await self.risk_rule_repo.increment_violation_count(rule.id)

            except Exception as e:
                log.error(f"Failed to evaluate rule {rule.id}: {e}")

        return triggered_alerts

    @measure("risk_management_create_alert_seconds")
    async def create_risk_alert(self, alert_data: RiskAlertIn) -> RiskAlertOut:
        """创建风险告警"""
        alert = await self.risk_alert_repo.create(alert_data)

        # 发送通知（这里可以集成消息队列）
        await self._send_alert_notification(alert)

        log.info(f"Created risk alert: {alert.alert_name} [{alert.severity}]")
        return alert

    @measure("risk_management_acknowledge_alert_seconds")
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[RiskAlertOut]:
        """确认告警"""
        update_data = RiskAlertUpdate(
            status='ACKNOWLEDGED',
            acknowledged_by=acknowledged_by,
            acknowledged_at=datetime.now()
        )

        alert = await self.risk_alert_repo.update(alert_id, update_data)
        if alert:
            log.info(f"Acknowledged alert: {alert_id}")
        return alert

    @measure("risk_management_resolve_alert_seconds")
    async def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[RiskAlertOut]:
        """解决告警"""
        update_data = RiskAlertUpdate(
            status='RESOLVED',
            resolved_by=resolved_by,
            resolved_at=datetime.now(),
            resolution_notes=resolution_notes
        )

        alert = await self.risk_alert_repo.update(alert_id, update_data)
        if alert:
            log.info(f"Resolved alert: {alert_id}")
        return alert

    @measure("risk_management_get_active_alerts_seconds")
    async def get_active_alerts(
        self,
        severity: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> List[RiskAlertOut]:
        """获取活跃告警"""
        query_params = RiskAlertQuery(
            status='ACTIVE',
            severity=severity,
            target_type=target_type,
            is_active=True,
            limit=1000
        )
        return await self.risk_alert_repo.list(query_params)

    @measure("risk_management_get_alert_stats_seconds")
    async def get_alert_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取告警统计"""
        start_date = datetime.now() - timedelta(days=days)

        # 获取时间范围内的告警
        query_params = RiskAlertQuery(limit=10000)
        alerts = await self.risk_alert_repo.list(query_params)

        # 过滤时间范围
        recent_alerts = [a for a in alerts if a.created_at >= start_date]

        # 统计数据
        total_alerts = len(recent_alerts)
        active_alerts = len([a for a in recent_alerts if a.status == 'ACTIVE'])
        critical_alerts = len([a for a in recent_alerts if a.severity == 'CRITICAL'])
        high_alerts = len([a for a in recent_alerts if a.severity == 'HIGH'])
        medium_alerts = len([a for a in recent_alerts if a.severity == 'MEDIUM'])
        low_alerts = len([a for a in recent_alerts if a.severity == 'LOW'])

        acknowledged_alerts = len([a for a in recent_alerts if a.status == 'ACKNOWLEDGED'])
        resolved_alerts = len([a for a in recent_alerts if a.status == 'RESOLVED'])
        dismissed_alerts = len([a for a in recent_alerts if a.status == 'DISMISSED'])

        # 按类型统计
        alerts_by_type = {}
        for alert in recent_alerts:
            alerts_by_type[alert.alert_type] = alerts_by_type.get(alert.alert_type, 0) + 1

        # 按严重程度统计
        alerts_by_severity = {
            'CRITICAL': critical_alerts,
            'HIGH': high_alerts,
            'MEDIUM': medium_alerts,
            'LOW': low_alerts
        }

        # 平均解决时间
        resolved_with_time = [
            a for a in recent_alerts
            if a.status == 'RESOLVED' and a.resolved_at and a.created_at
        ]

        avg_resolution_time = None
        if resolved_with_time:
            total_resolution_time = sum([
                (a.resolved_at - a.created_at).total_seconds() / 3600  # 小时
                for a in resolved_with_time
            ])
            avg_resolution_time = total_resolution_time / len(resolved_with_time)

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "medium_alerts": medium_alerts,
            "low_alerts": low_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "resolved_alerts": resolved_alerts,
            "dismissed_alerts": dismissed_alerts,
            "alerts_by_type": alerts_by_type,
            "alerts_by_severity": alerts_by_severity,
            "avg_resolution_time": round(avg_resolution_time, 2) if avg_resolution_time else None
        }

    async def _evaluate_single_rule(self, rule: RiskRuleOut, data: Dict[str, Any]) -> bool:
        """评估单个风险规则"""
        try:
            rule_config = rule.rule_config

            # 根据规则类型进行评估
            if rule.rule_type == 'THRESHOLD':
                return await self._evaluate_threshold_rule(rule, data)
            elif rule.rule_type == 'TREND':
                return await self._evaluate_trend_rule(rule, data)
            elif rule.rule_type == 'CORRELATION':
                return await self._evaluate_correlation_rule(rule, data)
            elif rule.rule_type == 'ANOMALY':
                return await self._evaluate_anomaly_rule(rule, data)
            else:
                log.warning(f"Unknown rule type: {rule.rule_type}")
                return False

        except Exception as e:
            log.error(f"Error evaluating rule {rule.id}: {e}")
            return False

    async def _evaluate_threshold_rule(self, rule: RiskRuleOut, data: Dict[str, Any]) -> bool:
        """评估阈值规则"""
        field_name = rule.rule_config.get('field_name')
        if not field_name or field_name not in data:
            return False

        value = Decimal(str(data[field_name]))
        threshold = rule.threshold_value
        operator = rule.rule_config.get('operator', 'gt')

        if operator == 'gt':
            return value > threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'eq':
            return value == threshold
        else:
            return False

    async def _evaluate_trend_rule(self, rule: RiskRuleOut, data: Dict[str, Any]) -> bool:
        """评估趋势规则"""
        # 简化实现，实际应该分析历史数据趋势
        field_name = rule.rule_config.get('field_name')
        trend_direction = rule.rule_config.get('trend_direction', 'up')

        if not field_name or field_name not in data:
            return False

        # 这里需要历史数据来计算趋势，暂时简化
        current_value = Decimal(str(data[field_name]))
        return current_value > rule.threshold_value if trend_direction == 'up' else current_value < rule.threshold_value

    async def _evaluate_correlation_rule(self, rule: RiskRuleOut, data: Dict[str, Any]) -> bool:
        """评估相关性规则"""
        # 简化实现，实际应该计算相关系数
        field1 = rule.rule_config.get('field1')
        field2 = rule.rule_config.get('field2')

        if not field1 or not field2 or field1 not in data or field2 not in data:
            return False

        # 简化的相关性检查
        value1 = Decimal(str(data[field1]))
        value2 = Decimal(str(data[field2]))
        correlation_threshold = rule.threshold_value

        # 这里应该有更复杂的相关性计算
        return abs(value1 - value2) > correlation_threshold

    async def _evaluate_anomaly_rule(self, rule: RiskRuleOut, data: Dict[str, Any]) -> bool:
        """评估异常检测规则"""
        # 简化实现，实际应该使用统计方法检测异常
        field_name = rule.rule_config.get('field_name')
        if not field_name or field_name not in data:
            return False

        value = Decimal(str(data[field_name]))
        # 简化的异常检测：超出阈值即为异常
        return abs(value) > rule.threshold_value

    async def _create_alert_from_rule(
        self,
        rule: RiskRuleOut,
        target_id: str,
        target_type: str,
        data: Dict[str, Any]
    ) -> RiskAlertOut:
        """从规则创建告警"""
        field_name = rule.rule_config.get('field_name', 'unknown')
        actual_value = Decimal(str(data.get(field_name, 0)))

        alert_data = RiskAlertIn(
            alert_name=f"{rule.rule_name} - {target_id}",
            alert_type=rule.rule_type,
            severity=self._determine_severity(rule, actual_value),
            rule_id=rule.id,
            target_id=target_id,
            target_type=target_type,
            threshold_value=rule.threshold_value,
            actual_value=actual_value,
            description=f"Risk rule '{rule.rule_name}' triggered for {target_type} {target_id}",
            alert_data=data,
            created_by="system"
        )

        return await self.risk_alert_repo.create(alert_data)

    def _determine_severity(self, rule: RiskRuleOut, actual_value: Decimal) -> str:
        """确定告警严重程度"""
        threshold = rule.threshold_value
        warning_threshold = rule.warning_threshold

        if warning_threshold:
            # 如果实际值超过警告阈值很多，升级严重程度
            if abs(actual_value - threshold) > abs(warning_threshold - threshold) * 2:
                return 'CRITICAL'
            elif abs(actual_value - threshold) > abs(warning_threshold - threshold):
                return 'HIGH'
            else:
                return 'MEDIUM'
        else:
            # 没有警告阈值时，根据优先级确定严重程度
            priority = rule.priority
            if priority <= 2:
                return 'CRITICAL'
            elif priority <= 5:
                return 'HIGH'
            elif priority <= 8:
                return 'MEDIUM'
            else:
                return 'LOW'

    async def _send_alert_notification(self, alert: RiskAlertOut) -> None:
        """发送告警通知"""
        # 这里应该集成消息队列或通知服务
        # 暂时只记录日志
        log.info(f"Alert notification: {alert.alert_name} [{alert.severity}]")

        # 未来可以集成邮件、短信、Slack等通知方式
        # if alert.severity in ['CRITICAL', 'HIGH']:
        #     await self._send_urgent_notification(alert)
        # else:
        #     await self._send_regular_notification(alert)