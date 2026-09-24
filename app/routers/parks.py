from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import ParkType

router = APIRouter(prefix="/parks", tags=["产业园区管理"])


@router.post("/", response_model=schemas.IndustrialPark, summary="创建产业园区")
def create_park(park_in: schemas.IndustrialParkCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(crud.models.IndustrialPark)
        .filter(crud.models.IndustrialPark.name == park_in.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="园区名称已存在")
    return crud.create_park(db=db, obj_in=park_in)


@router.get("/", response_model=List[schemas.IndustrialPark], summary="查询园区列表")
def list_parks(
    park_type: Optional[ParkType] = Query(None, description="园区类型"),
    city: Optional[str] = Query(None, description="所在城市"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.list_parks(
        db=db,
        park_type=park_type.value if park_type else None,
        city=city,
        skip=skip,
        limit=limit,
    )


@router.get("/{park_id}", response_model=schemas.IndustrialPark, summary="查询园区详情")
def get_park(park_id: int, db: Session = Depends(get_db)):
    park = crud.get_park(db, park_id=park_id)
    if not park:
        raise HTTPException(status_code=404, detail="园区不存在")
    return park


@router.put("/{park_id}", response_model=schemas.IndustrialPark, summary="更新园区信息")
def update_park(
    park_id: int,
    park_in: schemas.IndustrialParkUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_park(db, park_id=park_id, obj_in=park_in)
    if not updated:
        raise HTTPException(status_code=404, detail="园区不存在")
    return updated


@router.delete("/{park_id}", summary="删除园区")
def delete_park(park_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_park(db, park_id=park_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="园区不存在")
    return {"message": "删除成功", "park_id": park_id}
