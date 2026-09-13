"""异常上报 + 整改跟踪"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Incident, Rectification
from ..schemas import (IncidentCreate, IncidentOut, RectificationComplete,
                       RectificationCreate, RectificationOut, RectificationVerify)

router = APIRouter(prefix="/api", tags=["异常与整改"])


def rect_to_out(r: Rectification) -> dict:
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["overdue"] = r.deadline < date.today() and r.status not in ("已完成",)
    return d


def incident_to_out(i: Incident) -> dict:
    d = {c.name: getattr(i, c.name) for c in i.__table__.columns}
    d["rectifications"] = [rect_to_out(r) for r in i.rectifications]
    return d


# ---------- 异常上报 ----------
@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    category: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Incident)
    if category:
        q = q.filter(Incident.category == category)
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)
    if keyword:
        q = q.filter(Incident.title.contains(keyword))
    return [incident_to_out(i) for i in q.order_by(Incident.reported_at.desc()).all()]


@router.post("/incidents", response_model=IncidentOut, status_code=201)
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    obj = Incident(**data.model_dump(), reported_at=datetime.now())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


@router.post("/incidents/{incident_id}/close", response_model=IncidentOut)
def close_incident(incident_id: int, db: Session = Depends(get_db)):
    obj = db.get(Incident, incident_id)
    if not obj:
        raise HTTPException(404, "异常工单不存在")
    obj.status = "已关闭"
    obj.closed_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


@router.delete("/incidents/{incident_id}", status_code=204)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    obj = db.get(Incident, incident_id)
    if not obj:
        raise HTTPException(404, "异常工单不存在")
    db.delete(obj)
    db.commit()


# ---------- 整改跟踪 ----------
@router.get("/rectifications", response_model=list[RectificationOut])
def list_rectifications(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Rectification)
    if status:
        q = q.filter(Rectification.status == status)
    return [rect_to_out(r) for r in q.order_by(Rectification.deadline).all()]


@router.post("/rectifications", response_model=RectificationOut, status_code=201)
def create_rectification(data: RectificationCreate, db: Session = Depends(get_db)):
    incident = db.get(Incident, data.incident_id)
    if not incident:
        raise HTTPException(404, "关联的异常工单不存在")
    obj = Rectification(**data.model_dump(), started_at=datetime.now(), status="整改中")
    incident.status = "整改中"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)


@router.post("/rectifications/{rect_id}/complete", response_model=RectificationOut)
def complete_rectification(rect_id: int, data: RectificationComplete, db: Session = Depends(get_db)):
    obj = db.get(Rectification, rect_id)
    if not obj:
        raise HTTPException(404, "整改任务不存在")
    if obj.status == "已完成":
        raise HTTPException(400, "该整改已完成")
    obj.status = "已完成"
    obj.completed_at = datetime.now()
    obj.result = data.result
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)


@router.post("/rectifications/{rect_id}/verify", response_model=RectificationOut)
def verify_rectification(rect_id: int, data: RectificationVerify, db: Session = Depends(get_db)):
    """验收整改任务；仅当工单下所有整改任务均验收通过后，工单才标记为已整改"""
    obj = db.get(Rectification, rect_id)
    if not obj:
        raise HTTPException(404, "整改任务不存在")
    if obj.status != "已完成":
        raise HTTPException(400, "请先完成整改再验收")
    if obj.verified_at:
        raise HTTPException(400, "该整改任务已验收")
    obj.verifier = data.verifier
    obj.verified_at = datetime.now()
    # 全部整改任务均完成且验收通过，工单才可标记为已整改
    all_verified = all(
        r.status == "已完成" and (r.verified_at is not None or r.id == obj.id)
        for r in obj.incident.rectifications
    )
    if all_verified:
        obj.incident.status = "已整改"
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)
