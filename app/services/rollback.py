"""受控回退：权限校验、历史一致性检查、幂等执行与审计记录。

与手动状态流转（status_flow）的区别：
- 允许跨级退回（如「建设中」直接退回「洽谈中」），但必须由授权操作人发起；
- 执行前检查已完成里程碑与月度产能报告，避免破坏历史一致性；
- 保留立项信息与未完成里程碑，并作为受影响记录写入状态日志；
- 通过 request_id 幂等：重复提交同一回退请求返回首次执行结果。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..enums import MilestoneStatus, ProjectStatus
from ..errors import ERROR_ROLLBACK, fmt
from .status_flow import PROJECT_STATUS_ORDER

ROLLBACK_ACTION = "rollback"


class RollbackPermissionError(PermissionError):
    """操作人不在受控回退授权名单内。"""


class RollbackValidationError(ValueError):
    """回退请求不满足执行条件（目标非法或会破坏历史一致性）。"""


@dataclass
class RollbackOutcome:
    log: models.ProjectStatusLog
    affected_records: Dict[str, Any]
    replay: bool


def authorized_rollback_operators() -> List[str]:
    return [
        name.strip()
        for name in settings.ROLLBACK_OPERATOR_ALLOWLIST.split(",")
        if name.strip()
    ]


def ensure_operator_authorized(operator: str) -> None:
    if operator not in authorized_rollback_operators():
        raise RollbackPermissionError(
            fmt(ERROR_ROLLBACK["operator_not_authorized"], operator=operator)
        )


def find_rollback_log(
    db: Session, project_id: int, request_id: str
) -> Optional[models.ProjectStatusLog]:
    return (
        db.query(models.ProjectStatusLog)
        .filter(
            models.ProjectStatusLog.project_id == project_id,
            models.ProjectStatusLog.request_id == request_id,
            models.ProjectStatusLog.action == ROLLBACK_ACTION,
        )
        .first()
    )


def validate_rollback_target(
    from_status: ProjectStatus, to_status: ProjectStatus
) -> None:
    if from_status == to_status:
        raise RollbackValidationError(
            fmt(ERROR_ROLLBACK["same_status"], status=to_status.value)
        )
    from_idx = PROJECT_STATUS_ORDER.index(from_status)
    to_idx = PROJECT_STATUS_ORDER.index(to_status)
    if to_idx > from_idx:
        raise RollbackValidationError(
            fmt(
                ERROR_ROLLBACK["forward_not_allowed"],
                from_status=from_status.value,
                to_status=to_status.value,
            )
        )


def collect_rollback_blockers(db: Session, project: models.Project) -> List[str]:
    """会破坏历史一致性的情形，返回具体拒绝原因列表。"""
    blockers: List[str] = []
    completed = [
        m for m in project.milestones if m.status == MilestoneStatus.COMPLETED
    ]
    if completed:
        names = "、".join(f"「{m.name}」" for m in completed)
        blockers.append(fmt(ERROR_ROLLBACK["completed_milestones"], names=names))
    report_count = (
        db.query(models.MonthlyCapacityReport)
        .filter(models.MonthlyCapacityReport.project_id == project.id)
        .count()
    )
    if report_count:
        blockers.append(
            fmt(ERROR_ROLLBACK["capacity_reports"], count=report_count)
        )
    return blockers


def build_affected_records(db: Session, project: models.Project) -> Dict[str, Any]:
    """汇总回退后仍然有效的记录：立项依据（保留）与未完成里程碑。"""
    pending = sorted(
        (m for m in project.milestones if m.status != MilestoneStatus.COMPLETED),
        key=lambda m: m.sequence,
    )
    report_count = (
        db.query(models.MonthlyCapacityReport)
        .filter(models.MonthlyCapacityReport.project_id == project.id)
        .count()
    )
    approval = project.approval
    return {
        "preserved_approval": (
            {
                "id": approval.id,
                "approval_number": approval.approval_number,
                "approval_date": approval.approval_date.isoformat(),
                "approving_authority": approval.approving_authority,
                "agreed_investment_10k": approval.agreed_investment_10k,
            }
            if approval
            else None
        ),
        "pending_milestones": [
            {
                "id": m.id,
                "sequence": m.sequence,
                "name": m.name,
                "milestone_type": m.milestone_type.value,
                "status": m.status.value,
            }
            for m in pending
        ],
        "capacity_report_count": report_count,
    }


def _outcome_from_log(
    log: models.ProjectStatusLog, replay: bool
) -> RollbackOutcome:
    affected = {}
    if log.affected_records:
        try:
            affected = json.loads(log.affected_records)
        except ValueError:
            affected = {}
    return RollbackOutcome(log=log, affected_records=affected, replay=replay)


def load_rollback_outcome(
    db: Session, project_id: int, request_id: str
) -> Optional[RollbackOutcome]:
    """按幂等键读取已执行的回退结果（用于重复提交与并发冲突后的稳定返回）。"""
    log = find_rollback_log(db, project_id, request_id)
    if log is None:
        return None
    return _outcome_from_log(log, replay=True)


def execute_controlled_rollback(
    db: Session,
    project: models.Project,
    *,
    to_status: ProjectStatus,
    operator: str,
    reason: str,
    request_id: str,
    remarks: Optional[str] = None,
) -> RollbackOutcome:
    # 幂等：同一项目同一 request_id 已执行过，直接返回首次结果
    existing = find_rollback_log(db, project.id, request_id)
    if existing:
        return _outcome_from_log(existing, replay=True)

    validate_rollback_target(project.status, to_status)

    blockers = collect_rollback_blockers(db, project)
    if blockers:
        raise RollbackValidationError("；".join(blockers))

    affected = build_affected_records(db, project)

    from_status = project.status
    project.status = to_status
    log = models.ProjectStatusLog(
        project_id=project.id,
        from_status=from_status,
        to_status=to_status,
        action=ROLLBACK_ACTION,
        request_id=request_id,
        operator=operator,
        reason=reason,
        remarks=remarks,
        affected_records=json.dumps(affected, ensure_ascii=False),
        changed_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    return RollbackOutcome(log=log, affected_records=affected, replay=False)
