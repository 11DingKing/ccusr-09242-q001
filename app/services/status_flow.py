from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from .. import models
from ..enums import ProjectStatus, MilestoneStatus, MilestoneType


PROJECT_STATUS_ORDER = [
    ProjectStatus.ATTRACTING_INVESTMENT,
    ProjectStatus.NEGOTIATING,
    ProjectStatus.ESTABLISHED,
    ProjectStatus.UNDER_CONSTRUCTION,
    ProjectStatus.COMMISSIONED,
]

FORWARD_TRANSITIONS = {
    (ProjectStatus.ATTRACTING_INVESTMENT, ProjectStatus.NEGOTIATING),
    (ProjectStatus.NEGOTIATING, ProjectStatus.ESTABLISHED),
    (ProjectStatus.ESTABLISHED, ProjectStatus.UNDER_CONSTRUCTION),
    (ProjectStatus.UNDER_CONSTRUCTION, ProjectStatus.COMMISSIONED),
}

ROLLBACK_TRANSITIONS = {
    (ProjectStatus.NEGOTIATING, ProjectStatus.ATTRACTING_INVESTMENT),
    (ProjectStatus.ESTABLISHED, ProjectStatus.NEGOTIATING),
    (ProjectStatus.UNDER_CONSTRUCTION, ProjectStatus.ESTABLISHED),
    (ProjectStatus.COMMISSIONED, ProjectStatus.UNDER_CONSTRUCTION),
}


class StatusTransitionError(ValueError):
    pass


ERROR_MSGS = {
    "same_status": "项目已是「{status}」状态，无需变更",
    "rollback_requires_reason": "不允许从「{from_status}」退回到「{to_status}」，必须填写退回原因",
    "skip_forward": "不允许从「{from_status}」跳到「{to_status}」，需依次经过：{skipped}",
    "illegal_transition": "不允许从「{from_status}」变更为「{to_status}」",
}


def _format_status(status: Optional[ProjectStatus]) -> str:
    return status.value if status else "初始"


def validate_status_transition(
    from_status: ProjectStatus,
    to_status: ProjectStatus,
    reason: Optional[str] = None,
) -> None:
    if from_status == to_status:
        raise StatusTransitionError(
            ERROR_MSGS["same_status"].format(status=to_status.value)
        )

    if (from_status, to_status) in FORWARD_TRANSITIONS:
        return

    if (from_status, to_status) in ROLLBACK_TRANSITIONS:
        if not reason or not reason.strip():
            raise StatusTransitionError(
                ERROR_MSGS["rollback_requires_reason"].format(
                    from_status=from_status.value,
                    to_status=to_status.value,
                )
            )
        return

    from_idx = PROJECT_STATUS_ORDER.index(from_status)
    to_idx = PROJECT_STATUS_ORDER.index(to_status)
    if to_idx > from_idx:
        skipped = [s.value for s in PROJECT_STATUS_ORDER[from_idx + 1 : to_idx]]
        raise StatusTransitionError(
            ERROR_MSGS["skip_forward"].format(
                from_status=from_status.value,
                to_status=to_status.value,
                skipped=" → ".join(skipped),
            )
        )
    raise StatusTransitionError(
        ERROR_MSGS["illegal_transition"].format(
            from_status=from_status.value,
            to_status=to_status.value,
        )
    )


def _write_status_log(
    db: Session,
    project_id: int,
    from_status: Optional[ProjectStatus],
    to_status: ProjectStatus,
    operator: Optional[str] = None,
    reason: Optional[str] = None,
    remarks: Optional[str] = None,
) -> None:
    log = models.ProjectStatusLog(
        project_id=project_id,
        from_status=from_status,
        to_status=to_status,
        operator=operator,
        reason=reason,
        remarks=remarks,
        changed_at=datetime.utcnow(),
    )
    db.add(log)


def transition_project_status(
    db: Session,
    project: models.Project,
    to_status: ProjectStatus,
    operator: Optional[str] = None,
    reason: Optional[str] = None,
    remarks: Optional[str] = None,
    skip_validation: bool = False,
) -> models.Project:
    from_status = project.status

    if not skip_validation:
        validate_status_transition(from_status, to_status, reason=reason)

    project.status = to_status
    _write_status_log(
        db,
        project_id=project.id,
        from_status=from_status,
        to_status=to_status,
        operator=operator,
        reason=reason,
        remarks=remarks,
    )
    db.flush()
    return project


def trigger_status_after_intent(
    db: Session,
    project: models.Project,
    operator: Optional[str] = None,
) -> None:
    if project.status != ProjectStatus.ATTRACTING_INVESTMENT:
        return
    transition_project_status(
        db,
        project=project,
        to_status=ProjectStatus.NEGOTIATING,
        operator=operator,
        reason="收到合作意向，转入洽谈阶段",
        skip_validation=True,
    )


def trigger_status_after_approval(
    db: Session,
    project: models.Project,
    approval_number: str,
    operator: Optional[str] = None,
) -> None:
    if project.status != ProjectStatus.NEGOTIATING:
        return
    transition_project_status(
        db,
        project=project,
        to_status=ProjectStatus.ESTABLISHED,
        operator=operator,
        reason=f"正式立项，文号：{approval_number}",
        skip_validation=True,
    )


def _has_any_milestone_in_progress(milestones) -> bool:
    return any(m.status == MilestoneStatus.IN_PROGRESS for m in milestones)


def _is_official_production_completed(milestones) -> bool:
    if not milestones:
        return False
    last_m = max(milestones, key=lambda m: m.sequence)
    return (
        last_m.milestone_type == MilestoneType.OFFICIAL_PRODUCTION
        and last_m.status == MilestoneStatus.COMPLETED
    )


def trigger_status_after_milestone_update(
    db: Session,
    project: models.Project,
    milestones,
    operator: Optional[str] = None,
) -> None:
    if _is_official_production_completed(milestones):
        if project.status == ProjectStatus.UNDER_CONSTRUCTION:
            transition_project_status(
                db,
                project=project,
                to_status=ProjectStatus.COMMISSIONED,
                operator=operator,
                reason="正式投产里程碑完成，项目已投产",
                skip_validation=True,
            )
        return

    if _has_any_milestone_in_progress(milestones):
        if project.status == ProjectStatus.ESTABLISHED:
            transition_project_status(
                db,
                project=project,
                to_status=ProjectStatus.UNDER_CONSTRUCTION,
                operator=operator,
                reason="里程碑推进中，项目进入建设期",
                skip_validation=True,
            )
