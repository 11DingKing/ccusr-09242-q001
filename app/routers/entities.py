from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from ..database import get_db
from .. import crud, schemas
from ..enums import Region

router = APIRouter(prefix="/entities", tags=["合作主体管理"])


@router.post("/", response_model=schemas.Entity, summary="创建合作主体")
def create_entity(entity_in: schemas.EntityCreate, db: Session = Depends(get_db)):
    existing = crud.get_entity_by_name(db, name=entity_in.name)
    if existing:
        raise HTTPException(status_code=400, detail="主体名称已存在")
    return crud.create_entity(db=db, obj_in=entity_in)


@router.get("/", response_model=List[schemas.EntityListItem], summary="查询主体列表")
def list_entities(
    region: Optional[Region] = Query(None, description="按地区筛选：东盟方/广西方"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return crud.list_entities(db=db, region=region.value if region else None, skip=skip, limit=limit)


@router.get("/{entity_id}", response_model=schemas.Entity, summary="查询主体详情")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    entity = crud.get_entity(db, entity_id=entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="主体不存在")
    return entity


@router.put("/{entity_id}", response_model=schemas.Entity, summary="更新主体信息")
def update_entity(
    entity_id: int,
    entity_in: schemas.EntityUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_entity(db, entity_id=entity_id, obj_in=entity_in)
    if not updated:
        raise HTTPException(status_code=404, detail="主体不存在")
    return updated


@router.delete("/{entity_id}", summary="删除主体")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_entity(db, entity_id=entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="主体不存在")
    return {"message": "删除成功", "entity_id": entity_id}


@router.post(
    "/{entity_id}/capabilities",
    response_model=schemas.EntityCapability,
    summary="为主体添加加工品类与产能",
)
def add_capability(
    entity_id: int,
    cap_in: schemas.EntityCapabilityCreate,
    db: Session = Depends(get_db),
):
    entity = crud.get_entity(db, entity_id=entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="主体不存在")
    return crud.add_entity_capability(db, entity_id=entity_id, cap_in=cap_in)


@router.delete(
    "/capabilities/{capability_id}",
    summary="删除主体的加工品类记录",
)
def delete_capability(capability_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_entity_capability(db, capability_id=capability_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="产能记录不存在")
    return {"message": "删除成功", "capability_id": capability_id}
