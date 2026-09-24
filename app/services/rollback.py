"""受控项目状态回退服务。

只有白名单角色（招商主管等）可人工发起；回退前检查未完成里程碑、
已生效立项信息与投产后业务数据，对会破坏历史一致性的请求给出具体拒绝原因。

每次请求（无论执行还是拒绝）都按 request_id 幂等落库，重启后仍可查询，
重复提交返回首次的稳定结果。立项信息与里程碑始终保留，不做物理删除。
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..enums import ProjectStatus, MilestoneStatus, MilestoneType
from .status_flow import PROJECT_STATUS_ORDER, ROLLBACK_TRANSITIONS


# 允许发起受控回退的岗位角色
ALLOWED_ROLLBACK_ROLES = {"招商主管"}


class RollbackPermissionError(PermissionError):
    """操作人不具备受控回退权限。"""


class RollbackRequestError(ValueError):
    """请求本身非法（目标状态不允许、request_id 冲突等）。"""


def _previous_status(status: ProjectStatus) -> Optional[ProjectStatus]:
    idx = PROJECT_STATUS_ORDER.index(status)
    if idx == 0:
        return None
    return PROJECT_STATUS_ORDER[idx - 1]


def _count(db: Session, model, project_id: int) -> int:
    return (
        db.query(model)
        .filter(model.project_id == project_id)
       .count()
    )


def _build_affected_records(
    db: Session,
    project: models.Project,
) -> List[dict]:
    """汇总本次回退涉及、需要保留或核对的业务记录快照。"""
    records: List[dict] = []

    if project.approval is not None:
        records.append(
            {
                "type": "approval",
                "id": project.approval.id,
                "name": project.approval.approval_number,
                "status": None,
                "effect": "retained",
                "detail": "回退后保留已生效立项信息（立项依据），不作删除或作废",
            }
        )

    for milestone in sorted(project.milestones, key=lambda m: m.sequence):
        records.append(
            {
                "type": "milestone",
                "id": milestone.id,
                "name": milestone.name,
                "status": milestone.status.value,
                "effect": "retained",
                "detail": (
                    f"第{milestone.sequence}个里程碑，回退后保持「{milestone.status.value}」"
                    "状态不变，进度事实继续可查"
                ),
            }
        )

    report_count = _count(db, models.MonthlyCapacityReport, project.id)
    if report_count:
        records.append(
            {
                "type": "monthly_capacity_report",
                "id": None,
                "name": f"月度产能报告×{report_count}",
                "status": None,
                "effect": "checked",
                "detail": f"项目已登记 {report_count} 条月度产能报告，投产业务数据已生效",
            }
        )

    follow_up_count = _count(db, models.CapacityFollowUp, project.id)
    if follow_up_count:
        records.append(
            {
                "type": "capacity_follow_up",
                "id": None,
                "name": f"产能跟进事项×{follow_up_count}",
                "status": None,
                "effect": "checked",
                "detail": f"项目存在 {follow_up_count} 条产能跟进事项，投产后处置流程已启动",
            }
        )

    intent_count = _count(db, models.CooperationIntent, project.id)
    if intent_count:
        records.append(
            {
                "type": "cooperation_intent",
                "id": None,
                "name": f"合作意向×{intent_count}",
                "status": None,
                "effect": "retained",
                "detail": f"项目下 {intent_count} 条合作意向及洽谈记录保留不变",
            }
        )

    return records


def _consistency_reject_reasons(
    db: Session,
    project: models.Project,
    target_status: ProjectStatus,
) -> List[str]:
    """根据目标阶段汇总会破坏历史一致性的具体原因；为空表示可以回退。"""
    reasons: List[str] = []
    milestones = sorted(project.milestones, key=lambda m: m.sequence)

    if target_status == ProjectStatus.NEGOTIATING:
        # 已立项 → 洽谈中：保留立项依据，但立项后任何里程碑进度都不能存在
        if project.approval is None:
            reasons.append(
                "项目缺少已生效立项信息，当前状态与立项数据不一致，"
                "无法按受控流程回退到洽谈阶段"
            )
        for milestone in milestones:
            if milestone.status != MilestoneStatus.NOT_STARTED:
                reasons.append(
                    f"里程碑「{milestone.name}」当前为「{milestone.status.value}」，"
                    "立项后的建设进度已经发生，回退洽谈将破坏进度历史一致性，"
                    "请先在建设阶段处置该里程碑"
                )

    elif target_status == ProjectStatus.ESTABLISHED:
        # 建设中 → 已立项：仍在推进/延期的里程碑没有闭合结论
        for milestone in milestones:
            if milestone.status in (
                MilestoneStatus.IN_PROGRESS,
                MilestoneStatus.DELAYED,
            ):
                reasons.append(
                    f"里程碑「{milestone.name}」尚未完成（当前状态："
                    f"「{milestone.status.value}」），回退已立项会造成在建里程碑失去阶段归属，"
                    "请先完成或关闭该里程碑后再发起回退"
                )

    elif target_status == ProjectStatus.UNDER_CONSTRUCTION:
        # 已投产 → 建设中：投产事实与投产后数据必须全部不存在
        if milestones:
            last_milestone = max(milestones, key=lambda m: m.sequence)
            if (
                last_milestone.milestone_type == MilestoneType.OFFICIAL_PRODUCTION
                and last_milestone.status == MilestoneStatus.COMPLETED
            ):
                actual = (
                    last_milestone.actual_date.isoformat()
                    if last_milestone.actual_date
                    else "日期未登记"
                )
                reasons.append(
                    f"正式投产里程碑「{last_milestone.name}」已于 {actual} 完成，"
                    "投产事实已生效并构成项目进入已投产的依据，不允许回退到建设中"
                )

        report_count = _count(db, models.MonthlyCapacityReport, project.id)
        if report_count:
            reasons.append(
                f"项目已登记 {report_count} 条月度产能报告，投产业务数据已生效，"
                "回退建设中将使产能数据失去合法阶段归属"
            )

        follow_up_count = _count(db, models.CapacityFollowUp, project.id)
        if follow_up_count:
            reasons.append(
                f"项目已生成 {follow_up_count} 条产能跟进事项，投产后处置流程已启动，"
                "不允许回退到建设中"
            )

    return reasons


def _get_project_for_rollback(db: Session, project_id: int):
    return (
        db.query(models.Project)
        .options(
            joinedload(models.Project.milestones),
            joinedload(models.Project.approval),
        )
        .filter(models.Project.id == project_id)
        .first()
    )


def submit_rollback(
    db: Session,
    project: models.Project,
    payload: schemas.ProjectRollbackRequest,
) -> Tuple[models.ProjectRollbackRequest, bool]:
    """提交受控回退请求，返回（请求记录, 是否实际执行）。

    同一 request_id 重复提交时直接返回首次的记录与结果，不重复执行。
    """
    target_status = payload.target_status or _previous_status(project.status)
    if target_status is None or (project.status, target_status) not in ROLLBACK_TRANSITIONS:
        raise RollbackRequestError(
            f"不允许从「{project.status.value}」受控回退到「"
            f"{target_status.value if target_status else '无'}」，"
            "受控回退仅支持相邻阶段，且招商中为初始状态不可回退"
        )

    existing = (
        db.query(models.ProjectRollbackRequest)
        .filter(models.ProjectRollbackRequest.request_id == payload.request_id)
        .first()
    )
    if existing is not None:
        if existing.project_id != project.id:
            raise RollbackRequestError(
                "request_id 已被其他项目的回退请求占用，请更换后再提交"
            )
        db.refresh(existing)
        return existing, existing.result == "applied"

    if payload.operator_role not in ALLOWED_ROLLBACK_ROLES:
        raise RollbackPermissionError(
            f"「{payload.operator_role}」无权发起项目受控回退，"
            f"仅限以下岗位：{'、'.join(sorted(ALLOWED_ROLLBACK_ROLES))}"
        )

    affected_records = _build_affected_records(db, project)
    reject_reasons = _consistency_reject_reasons(db, project, target_status)

    if reject_reasons:
        record = models.ProjectRollbackRequest(
            request_id=payload.request_id,
            project_id=project.id,
            operator=payload.operator,
            operator_role=payload.operator_role,
            reason=payload.reason,
            remarks=payload.remarks,
            from_status=project.status,
            to_status=target_status,
            result="rejected",
            reject_reasons=reject_reasons,
            affected_records=affected_records,
            status_log_id=None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, False

    status_log = models.ProjectStatusLog(
        project_id=project.id,
        from_status=project.status,
        to_status=target_status,
        operator=payload.operator,
        reason=payload.reason,
        remarks=payload.remarks,
        log_kind="rollback",
        request_id=payload.request_id,
        affected_records=affected_records,
    )
    db.add(status_log)
    project.status = target_status
    db.flush()

    record = models.ProjectRollbackRequest(
        request_id=payload.request_id,
        project_id=project.id,
        operator=payload.operator,
        operator_role=payload.operator_role,
        reason=payload.reason,
        remarks=payload.remarks,
        from_status=status_log.from_status,
        to_status=target_status,
        result="applied",
        reject_reasons=[],
        affected_records=affected_records,
        status_log_id=status_log.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    db.refresh(project)
    return record, True


def get_rollback_request(db: Session, request_id: str):
    return (
        db.query(models.ProjectRollbackRequest)
        .filter(models.ProjectRollbackRequest.request_id == request_id)
        .first()
    )


def list_rollback_requests(
    db: Session,
    project_id: Optional[int] = None,
    result: Optional[str] = None,
):
    query = db.query(models.ProjectRollbackRequest)
    if project_id is not None:
        query = query.filter(models.ProjectRollbackRequest.project_id == project_id)
    if result:
        query = query.filter(models.ProjectRollbackRequest.result == result)
    return query.order_by(
        models.ProjectRollbackRequest.created_at.desc(),
        models.ProjectRollbackRequest.id.desc(),
    ).all()
