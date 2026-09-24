from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Optional, Tuple

from .. import models, schemas
from ..enums import MilestoneStatus, MilestoneType
from .status_flow import trigger_status_after_milestone_update


class MilestoneStateError(ValueError):
    pass


MILESTONE_ERROR_MSGS = {
    "must_be_in_progress_first": "里程碑必须先标记为「进行中」，才能完成",
    "cannot_mark_in_progress": "里程碑当前为「{current}」，不可标记为「进行中」",
    "cannot_reset_to_not_started": "不允许将里程碑退回到「未启动」状态",
    "prerequisite_not_completed": "前置里程碑「{name}」尚未完成，不可推进当前里程碑",
}

DEFAULT_MILESTONE_TEMPLATES: List[Tuple[MilestoneType, str, int]] = [
    (MilestoneType.FOUNDATION, "项目奠基开工", 30),
    (MilestoneType.MAIN_STRUCTURE, "主体结构封顶", 210),
    (MilestoneType.EQUIPMENT_INSTALLATION, "设备安装调试", 300),
    (MilestoneType.TRIAL_PRODUCTION, "试生产", 360),
    (MilestoneType.OFFICIAL_PRODUCTION, "正式投产运营", 390),
]


def validate_milestone_state_transition(
    current_status: MilestoneStatus,
    new_status: Optional[MilestoneStatus],
) -> None:
    if new_status is None:
        return

    if new_status == MilestoneStatus.NOT_STARTED:
        raise MilestoneStateError(MILESTONE_ERROR_MSGS["cannot_reset_to_not_started"])

    if new_status == MilestoneStatus.COMPLETED:
        if current_status != MilestoneStatus.IN_PROGRESS:
            raise MilestoneStateError(MILESTONE_ERROR_MSGS["must_be_in_progress_first"])

    if new_status == MilestoneStatus.IN_PROGRESS:
        if current_status not in (
            MilestoneStatus.NOT_STARTED,
            MilestoneStatus.DELAYED,
            MilestoneStatus.IN_PROGRESS,
        ):
            raise MilestoneStateError(
                MILESTONE_ERROR_MSGS["cannot_mark_in_progress"].format(
                    current=current_status.value
                )
            )


def _get_previous_milestones(
    db: Session,
    project_id: int,
    sequence: int,
) -> List[models.ProjectMilestone]:
    return (
        db.query(models.ProjectMilestone)
        .filter(
            models.ProjectMilestone.project_id == project_id,
            models.ProjectMilestone.sequence < sequence,
        )
        .all()
    )


def validate_prerequisite_milestones(
    db: Session,
    milestone: models.ProjectMilestone,
    new_status: Optional[MilestoneStatus],
) -> None:
    if new_status not in (MilestoneStatus.IN_PROGRESS, MilestoneStatus.COMPLETED):
        return

    previous = _get_previous_milestones(db, milestone.project_id, milestone.sequence)
    for prev in previous:
        if prev.status != MilestoneStatus.COMPLETED:
            raise MilestoneStateError(
                MILESTONE_ERROR_MSGS["prerequisite_not_completed"].format(
                    name=prev.name
                )
            )


def build_default_milestones(
    approval_date: date,
) -> List[schemas.MilestoneCreate]:
    milestones = []
    for i, (mtype, mname, days_offset) in enumerate(DEFAULT_MILESTONE_TEMPLATES, 1):
        planned = approval_date + timedelta(days=days_offset)
        milestones.append(
            schemas.MilestoneCreate(
                sequence=i,
                milestone_type=mtype,
                name=mname,
                status=MilestoneStatus.NOT_STARTED,
                planned_date=planned,
                completion_rate=0.0,
            )
        )
    return milestones


def persist_milestones(
    db: Session,
    project_id: int,
    milestones: List[schemas.MilestoneCreate],
) -> None:
    for m in milestones:
        db_m = models.ProjectMilestone(
            project_id=project_id,
            **m.model_dump(),
        )
        db.add(db_m)


def update_milestone_fields(
    db: Session,
    milestone: models.ProjectMilestone,
    update_in: schemas.ProjectMilestoneUpdate,
) -> models.ProjectMilestone:
    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(milestone, field, value)
    db.flush()
    db.refresh(milestone)
    return milestone


def list_milestones_for_project(
    db: Session,
    project_id: int,
) -> List[models.ProjectMilestone]:
    return (
        db.query(models.ProjectMilestone)
        .filter(models.ProjectMilestone.project_id == project_id)
        .order_by(models.ProjectMilestone.sequence)
        .all()
    )


def process_milestone_update(
    db: Session,
    milestone: models.ProjectMilestone,
    update_in: schemas.ProjectMilestoneUpdate,
    operator: Optional[str] = None,
) -> models.ProjectMilestone:
    validate_milestone_state_transition(milestone.status, update_in.status)
    validate_prerequisite_milestones(db, milestone, update_in.status)

    updated = update_milestone_fields(db, milestone, update_in)

    project = (
        db.query(models.Project)
        .filter(models.Project.id == milestone.project_id)
        .first()
    )
    if project:
        all_milestones = list_milestones_for_project(db, project.id)
        trigger_status_after_milestone_update(
            db, project, all_milestones, operator=operator
        )

    db.commit()
    db.refresh(updated)
    return updated
