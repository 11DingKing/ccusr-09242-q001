from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import ProjectStatus
from ..errors import HTTPStatus, ERROR_NOT_FOUND, ERROR_DUPLICATE
from ..services.rollback import RollbackPermissionError, RollbackRequestError

router = APIRouter(prefix="/projects", tags=["合作项目管理"])


def _rollback_response(project, record) -> schemas.ProjectRollbackResponse:
    # project_status 取该请求落定后的状态：执行成功为目标状态，被拒则保持原状态。
    # 仅依赖持久化记录，保证同一 request_id 重放得到完全一致的响应。
    project_status = record.to_status if record.result == "applied" else record.from_status
    return schemas.ProjectRollbackResponse(
        request_id=record.request_id,
        project_id=record.project_id,
        result=record.result,
        from_status=record.from_status,
        to_status=record.to_status,
        operator=record.operator,
        operator_role=record.operator_role,
        reason=record.reason,
        reject_reasons=list(record.reject_reasons or []),
        affected_records=list(record.affected_records or []),
        status_log_id=record.status_log_id,
        created_at=record.created_at,
        project_status=project_status,
    )


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


@router.get(
    "/rollback-requests",
    response_model=List[schemas.ProjectRollbackRecord],
    summary="审计查询：受控回退请求列表",
)
def list_rollback_requests(
    project_id: Optional[int] = Query(None, description="按项目筛选"),
    result: Optional[str] = Query(
        None,
        description="按结果筛选：applied（已执行）/ rejected（已拒绝）",
    ),
    db: Session = Depends(get_db),
):
    if result and result not in ("applied", "rejected"):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="result 仅支持 applied 或 rejected",
        )
    if project_id is not None and not crud.get_project(db, project_id=project_id):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return crud.list_rollback_requests(db, project_id=project_id, result=result)


@router.get(
    "/rollback-requests/{request_id}",
    response_model=schemas.ProjectRollbackRecord,
    summary="审计查询：按幂等键查询单次受控回退请求",
)
def get_rollback_request(request_id: str, db: Session = Depends(get_db)):
    record = crud.get_rollback_request(db, request_id=request_id)
    if not record:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="回退请求不存在",
        )
    return record


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
    response_model=schemas.ProjectRollbackResponse,
    summary="受控回退：仅限授权角色人工发起，带业务一致性校验与幂等审计",
)
def rollback_project(
    project_id: int,
    req: schemas.ProjectRollbackRequest,
    db: Session = Depends(get_db),
):
    try:
        outcome = crud.submit_project_rollback(
            db, project_id=project_id, payload=req
        )
    except RollbackPermissionError as e:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e))
    except RollbackRequestError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))
    if not outcome:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    project, record, applied = outcome
    if not applied:
        # 首次因一致性条件被拒、或同一 request_id 重放，都返回稳定的 409 与拒绝明细
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail={
                "message": "回退条件不满足，请求已记录但未执行",
                "request_id": record.request_id,
                "reject_reasons": list(record.reject_reasons or []),
                "affected_records": list(record.affected_records or []),
            },
        )
    return _rollback_response(project, record)


@router.get(
    "/{project_id}/status-logs",
    response_model=List[schemas.ProjectStatusLog],
    summary="项目状态变更日志",
)
def get_status_logs(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return crud.get_project_status_logs(db, project_id=project_id)
