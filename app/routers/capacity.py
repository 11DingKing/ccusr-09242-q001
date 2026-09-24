from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import FollowUpStatus, FollowUpPriority
from ..errors import (
    HTTPStatus,
    ERROR_NOT_FOUND,
    ERROR_OPERATION_FAILED,
)

router = APIRouter(prefix="/capacity", tags=["投产后产能兑现跟踪"])


@router.post(
    "/reports",
    response_model=schemas.MonthlyCapacityReport,
    summary="登记月度产能（自动计算达产率，低于承诺时自动生成跟进事项）",
)
def create_capacity_report(
    report_in: schemas.MonthlyCapacityReportCreate,
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id=report_in.project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    try:
        result = crud.create_capacity_report(db=db, obj_in=report_in)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e))
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ERROR_OPERATION_FAILED["capacity_report"],
        )
    return result


@router.get(
    "/reports",
    response_model=List[schemas.MonthlyCapacityReport],
    summary="查询月度产能登记列表",
)
def list_capacity_reports(
    project_id: Optional[int] = Query(None, description="项目ID筛选"),
    year: Optional[int] = Query(None, description="年度筛选"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.list_capacity_reports(
        db=db, project_id=project_id, year=year, skip=skip, limit=limit
    )


@router.get(
    "/reports/{report_id}",
    response_model=schemas.MonthlyCapacityReport,
    summary="查询单条月度产能登记详情",
)
def get_capacity_report(report_id: int, db: Session = Depends(get_db)):
    report = crud.get_capacity_report(db, report_id=report_id)
    if not report:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["capacity_report"],
        )
    return report


@router.put(
    "/reports/{report_id}",
    response_model=schemas.MonthlyCapacityReport,
    summary="更新月度产能登记",
)
def update_capacity_report(
    report_id: int,
    report_in: schemas.MonthlyCapacityReportUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_capacity_report(db, report_id=report_id, obj_in=report_in)
    if not updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["capacity_report"],
        )
    return updated


@router.delete("/reports/{report_id}", summary="删除月度产能登记")
def delete_capacity_report(report_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_capacity_report(db, report_id=report_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["capacity_report"],
        )
    return {"message": "删除成功", "report_id": report_id}


@router.post(
    "/follow-ups",
    response_model=schemas.CapacityFollowUp,
    summary="手动创建产能跟进事项",
)
def create_follow_up(
    fu_in: schemas.CapacityFollowUpCreate,
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id=fu_in.project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    return crud.create_follow_up(db=db, obj_in=fu_in)


@router.get(
    "/follow-ups",
    response_model=List[schemas.CapacityFollowUp],
    summary="查询产能跟进事项列表",
)
def list_follow_ups(
    project_id: Optional[int] = Query(None, description="项目ID筛选"),
    status: Optional[FollowUpStatus] = Query(None, description="跟进状态筛选"),
    priority: Optional[FollowUpPriority] = Query(None, description="优先级筛选"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.list_follow_ups(
        db=db,
        project_id=project_id,
        status=status,
        priority=priority,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/follow-ups/{follow_up_id}",
    response_model=schemas.CapacityFollowUp,
    summary="查询单条跟进事项详情",
)
def get_follow_up(follow_up_id: int, db: Session = Depends(get_db)):
    fu = crud.get_follow_up(db, follow_up_id=follow_up_id)
    if not fu:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["follow_up"],
        )
    return fu


@router.put(
    "/follow-ups/{follow_up_id}",
    response_model=schemas.CapacityFollowUp,
    summary="更新跟进事项（状态、责任人、解决方案等）",
)
def update_follow_up(
    follow_up_id: int,
    fu_in: schemas.CapacityFollowUpUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_follow_up(db, follow_up_id=follow_up_id, obj_in=fu_in)
    if not updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["follow_up"],
        )
    return updated


@router.delete("/follow-ups/{follow_up_id}", summary="删除跟进事项")
def delete_follow_up(follow_up_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_follow_up(db, follow_up_id=follow_up_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["follow_up"],
        )
    return {"message": "删除成功", "follow_up_id": follow_up_id}


@router.get(
    "/projects/{project_id}/curve",
    response_model=schemas.CapacityCurveResponse,
    summary="企业详情：承诺产能 vs 实际产能曲线数据",
)
def get_project_capacity_curve(project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["project"],
        )
    curve = crud.get_project_capacity_curve(db, project_id=project_id)
    if not curve:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ERROR_NOT_FOUND["capacity_curve"],
        )
    return curve


@router.get(
    "/statistics/overview",
    response_model=schemas.CapacityOverviewStatistics,
    summary="园区统计看板：达产率与本地采购汇总（全局+园区+品类）",
)
def get_capacity_overview_statistics(db: Session = Depends(get_db)):
    return crud.get_capacity_overview_statistics(db)


@router.get(
    "/statistics/parks",
    response_model=List[schemas.ParkCapacityStatistics],
    summary="园区维度达产率与采购额统计",
)
def get_parks_capacity_statistics(db: Session = Depends(get_db)):
    data = crud.get_capacity_overview_statistics(db)
    return data["parks"]


@router.get(
    "/statistics/categories",
    response_model=List[schemas.CategoryCapacityStatistics],
    summary="项目类型维度达产率与采购额统计",
)
def get_categories_capacity_statistics(db: Session = Depends(get_db)):
    data = crud.get_capacity_overview_statistics(db)
    return data["categories"]
