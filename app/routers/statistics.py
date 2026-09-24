from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, schemas

router = APIRouter(prefix="/statistics", tags=["统计分析"])


@router.get("/overview", response_model=schemas.OverallStatistics, summary="全局统计总览")
def get_overall_statistics(db: Session = Depends(get_db)):
    return crud.get_overall_statistics(db)


@router.get("/parks", response_model=list, summary="各园区落地统计")
def get_parks_statistics(db: Session = Depends(get_db)):
    data = crud.get_overall_statistics(db)
    return data["parks"]


@router.get("/categories", response_model=list, summary="各加工品类项目分布")
def get_categories_statistics(db: Session = Depends(get_db)):
    data = crud.get_overall_statistics(db)
    return data["categories"]
