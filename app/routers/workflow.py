from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import IntentStatus, ProjectStatus, MilestoneStatus
from ..errors import (
    HTTPStatus,
    ERROR_NOT_FOUND,
    ERROR_DUPLICATE,
    ERROR_STATUS,
    ERROR_OPERATION_FAILED,
    fmt,
)

router = APIRouter(prefix="/workflow", tags=["业务流转：意向-洽谈-立项-里程碑"])


@router.post("/intents", response_model=schemas.CooperationIntent, summary="提交合作意向")
def create_intent(intent_in: schemas.CooperationIntentCreate, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=intent_in.project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    if project.status != ProjectStatus.ATTRACTING_INVESTMENT:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=fmt(
                ERROR_STATUS["only_attracting_can_submit_intent"],
                status=project.status.value,
            ),
        )
    submitter = crud.get_entity(db, entity_id=intent_in.submitter_id)
    if not submitter:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["entity"],
        )
    if intent_in.counterparty_id:
        cp = crud.get_entity(db, entity_id=intent_in.counterparty_id)
        if not cp:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=ERROR_NOT_FOUND["entity"],
            )
    return crud.create_intent(db=db, obj_in=intent_in)


@router.get(
    "/intents",
    response_model=List[schemas.CooperationIntentListItem],
    summary="查询合作意向列表",
)
def list_intents(
    project_id: Optional[int] = Query(None),
    submitter_id: Optional[int] = Query(None),
    status: Optional[IntentStatus] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    intents = crud.list_intents(
        db=db, project_id=project_id, submitter_id=submitter_id, status=status, skip=skip, limit=limit
    )
    result = []
    for it in intents:
        item = schemas.CooperationIntentListItem(
            id=it.id,
            project_id=it.project_id,
            project_name=it.project.name if it.project else None,
            submitter_id=it.submitter_id,
            submitter_name=it.submitter.name if it.submitter else None,
            counterparty_id=it.counterparty_id,
            counterparty_name=it.counterparty.name if it.counterparty else None,
            status=it.status,
            cooperation_mode=it.cooperation_mode,
            proposed_investment_10k=it.proposed_investment_10k,
            submitted_at=it.submitted_at,
        )
        result.append(item)
    return result


@router.get(
    "/intents/{intent_id}",
    response_model=schemas.CooperationIntent,
    summary="查询合作意向详情（含洽谈记录）",
)
def get_intent(intent_id: int, db: Session = Depends(get_db)):
    intent = crud.get_intent(db, intent_id=intent_id)
    if not intent:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["intent"],
        )
    return intent


@router.put(
    "/intents/{intent_id}",
    response_model=schemas.CooperationIntent,
    summary="评审或更新合作意向",
)
def update_intent(
    intent_id: int,
    intent_in: schemas.CooperationIntentUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_intent(db, intent_id=intent_id, obj_in=intent_in)
    if not updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["intent"],
        )
    return updated


@router.post(
    "/intents/{intent_id}/negotiations",
    response_model=schemas.NegotiationRecord,
    summary="添加一轮洽谈记录",
)
def create_negotiation(
    intent_id: int,
    neg_in: schemas.NegotiationRecordCreate,
    db: Session = Depends(get_db),
):
    intent = crud.get_intent(db, intent_id=intent_id)
    if not intent:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["intent"],
        )
    return crud.create_negotiation(db, intent_id=intent_id, obj_in=neg_in)


@router.get(
    "/intents/{intent_id}/negotiations",
    response_model=List[schemas.NegotiationRecord],
    summary="查询所有洽谈记录",
)
def list_negotiations(intent_id: int, db: Session = Depends(get_db)):
    intent = crud.get_intent(db, intent_id=intent_id)
    if not intent:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["intent"],
        )
    return crud.list_negotiations(db, intent_id=intent_id)


@router.post(
    "/projects/{project_id}/approve",
    response_model=schemas.Project,
    summary="立项：录入立项信息+生成里程碑+状态转已立项",
)
def approve_project(
    project_id: int,
    approval_in: schemas.ProjectApprovalRequest,
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    if project.approval:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ERROR_DUPLICATE["approval"],
        )
    if project.status != ProjectStatus.NEGOTIATING:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=fmt(
                ERROR_STATUS["only_negotiating_can_approve"],
                status=project.status.value,
            ),
        )
    result = crud.approve_project(db, project_id=project_id, approval_in=approval_in)
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ERROR_OPERATION_FAILED["approval"],
        )
    return result


@router.get(
    "/projects/{project_id}/approval",
    response_model=schemas.ProjectApproval,
    summary="查询立项信息",
)
def get_approval(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    approval = crud.get_project_approval(db, project_id=project_id)
    if not approval:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["approval"],
        )
    return approval


@router.get(
    "/projects/{project_id}/milestones",
    response_model=List[schemas.ProjectMilestone],
    summary="查询项目里程碑进度",
)
def list_milestones(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return crud.list_milestones(db, project_id=project_id)


@router.post(
    "/projects/{project_id}/milestones",
    response_model=schemas.ProjectMilestone,
    summary="为项目新增里程碑",
)
def create_milestone(
    project_id: int,
    m_in: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    if project.status not in (ProjectStatus.ESTABLISHED, ProjectStatus.UNDER_CONSTRUCTION):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=fmt(
                ERROR_STATUS["only_established_or_uc_can_add_milestone"],
                status=project.status.value,
            ),
        )
    payload = schemas.ProjectMilestoneCreate(
        project_id=project_id, **m_in.model_dump()
    )
    return crud.create_milestone(db, obj_in=payload)


@router.put(
    "/milestones/{milestone_id}",
    response_model=schemas.ProjectMilestone,
    summary="更新里程碑状态/进度（完成后自动触发项目状态流转）",
)
def update_milestone(
    milestone_id: int,
    m_in: schemas.ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
):
    try:
        updated = crud.update_milestone(db, milestone_id=milestone_id, obj_in=m_in)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))
    if not updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["milestone"],
        )
    return updated
