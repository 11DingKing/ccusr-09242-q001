from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import ProjectStatus
from ..errors import HTTPStatus, ERROR_NOT_FOUND, ERROR_DUPLICATE
from ..services.rollback import RollbackPermissionError, RollbackValidationError

router = APIRouter(prefix="/projects", tags=["合作项目管理"])


@router.post("/", response_model=schemas.Project, summary="发布深加工合作项目")
def create_project(project_in: schemas.ProjectCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(crud.models.Project)
        .filter(crud.models.Project.name == project_in.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ERROR_DUPLICATE["project_name"],
        )
    if project_in.project_code:
        code_exist = (
            db.query(crud.models.Project)
            .filter(crud.models.Project.project_code == project_in.project_code)
            .first()
        )
        if code_exist:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=ERROR_DUPLICATE["project_code"],
            )
    return crud.create_project(db=db, obj_in=project_in)


@router.get("/", response_model=List[schemas.ProjectListItem], summary="查询项目列表")
def list_projects(
    status: Optional[ProjectStatus] = Query(None, description="项目状态筛选"),
    park_id: Optional[int] = Query(None, description="落地园区ID"),
    initiator_id: Optional[int] = Query(None, description="发起主体ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    projects = crud.list_projects(
        db=db,
        status=status,
        park_id=park_id,
        initiator_id=initiator_id,
        skip=skip,
        limit=limit,
    )
    result = []
    for p in projects:
        park_name = p.park.name if p.park else None
        initiator_name = p.initiator.name if p.initiator else None
        item = schemas.ProjectListItem(
            id=p.id,
            name=p.name,
            project_code=p.project_code,
            status=p.status,
            planned_investment_10k=p.planned_investment_10k,
            expected_annual_capacity_tonnes=p.expected_annual_capacity_tonnes,
            park_id=p.park_id,
            park_name=park_name,
            initiator_name=initiator_name,
            publish_date=p.publish_date,
            created_at=p.created_at,
        )
        result.append(item)
    return result


@router.get("/{project_id}", response_model=schemas.Project, summary="查询项目详情")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return project


@router.put("/{project_id}", response_model=schemas.Project, summary="更新项目信息")
def update_project(
    project_id: int,
    project_in: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_project(db, project_id=project_id, obj_in=project_in)
    if not updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return updated


@router.delete("/{project_id}", summary="删除项目")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_project(db, project_id=project_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return {"message": "删除成功", "project_id": project_id}


@router.post("/{project_id}/status", response_model=schemas.Project, summary="项目状态流转")
def change_project_status(
    project_id: int,
    req: schemas.StatusChangeRequest,
    db: Session = Depends(get_db),
):
    try:
        project = crud.change_project_status(
            db,
            project_id=project_id,
            to_status=req.to_status,
            operator=req.operator,
            reason=req.reason,
            remarks=req.remarks,
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return project


@router.post(
    "/{project_id}/rollback",
    response_model=schemas.RollbackResponse,
    summary="受控回退：授权操作人将项目退回到更早阶段",
)
def rollback_project(
    project_id: int,
    req: schemas.RollbackRequest,
    db: Session = Depends(get_db),
):
    try:
        outcome = crud.rollback_project(db, project_id=project_id, req=req)
    except RollbackPermissionError as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))
    except RollbackValidationError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))
    if outcome is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    log = outcome.log
    return schemas.RollbackResponse(
        project_id=project_id,
        log_id=log.id,
        request_id=log.request_id,
        idempotent_replay=outcome.replay,
        from_status=log.from_status,
        to_status=log.to_status,
        operator=log.operator,
        reason=log.reason,
        affected_records=outcome.affected_records,
        logged_at=log.changed_at,
    )


@router.get(
    "/{project_id}/status-logs",
    response_model=List[schemas.ProjectStatusLog],
    summary="项目状态变更日志",
)
def get_status_logs(
    project_id: int,
    action: Optional[str] = Query(
        None, description="按操作类型过滤，如 rollback 仅看受控回退记录"
    ),
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return crud.get_project_status_logs(db, project_id=project_id, action=action)
