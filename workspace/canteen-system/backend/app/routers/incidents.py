"""异常上报 + 整改跟踪（写操作仅食品安全管理员；上报人/验收人从登录账号取）"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, get_current_user, require_roles
from ..database import get_db
from ..models import Incident, Rectification
from ..schemas import (IncidentCreate, IncidentOut, RectificationComplete,
                       RectificationCreate, RectificationOut, RectificationVerify, VoidIn)
from ..services import log_action

router = APIRouter(prefix="/api", tags=["异常与整改"])

ADMIN_ONLY = Depends(require_roles(ROLE_ADMIN))


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
    view: str = "valid",  # valid有效(默认)/voided已作废/all全部
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(Incident)
    if view == "valid":
        q = q.filter(Incident.voided_at.is_(None))
    elif view == "voided":
        q = q.filter(Incident.voided_at.isnot(None))
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
def create_incident(data: IncidentCreate, db: Session = Depends(get_db),
                    user: dict = ADMIN_ONLY):
    payload = data.model_dump()
    payload["reporter"] = user["name"]  # 上报人强制取当前登录人
    obj = Incident(**payload, reported_at=datetime.now())
    db.add(obj)
    db.flush()
    log_action(db, user, "异常上报", "incident", obj.id, f"上报「{obj.title}」（{obj.category}/{obj.severity}）")
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


@router.post("/incidents/{incident_id}/close", response_model=IncidentOut)
def close_incident(incident_id: int, db: Session = Depends(get_db),
                   user: dict = ADMIN_ONLY):
    obj = db.get(Incident, incident_id)
    if not obj:
        raise HTTPException(404, "异常工单不存在")
    obj.status = "已关闭"
    obj.closed_at = datetime.now()
    log_action(db, user, "关闭工单", "incident", obj.id, f"关闭工单「{obj.title}」")
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


@router.post("/incidents/{incident_id}/void", response_model=IncidentOut)
def void_incident(incident_id: int, data: VoidIn, db: Session = Depends(get_db),
                  user: dict = ADMIN_ONLY):
    """作废工单（如误报）：原记录与整改链保留可查"""
    obj = db.get(Incident, incident_id)
    if not obj:
        raise HTTPException(404, "异常工单不存在")
    if obj.voided_at:
        raise HTTPException(400, "该工单已作废")
    if not data.reason.strip():
        raise HTTPException(400, "请填写作废原因")
    obj.voided_at = datetime.now()
    obj.voided_by = user["name"]
    obj.void_reason = data.reason.strip()
    log_action(db, user, "工单作废", "incident", obj.id,
               f"作废工单「{obj.title}」，原因：{obj.void_reason}")
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


@router.post("/incidents/{incident_id}/restore", response_model=IncidentOut)
def restore_incident(incident_id: int, db: Session = Depends(get_db),
                     user: dict = ADMIN_ONLY):
    """恢复误作废的工单"""
    obj = db.get(Incident, incident_id)
    if not obj:
        raise HTTPException(404, "异常工单不存在")
    if not obj.voided_at:
        raise HTTPException(400, "该工单未作废")
    log_action(db, user, "工单恢复", "incident", obj.id,
               f"恢复工单「{obj.title}」（原作废原因：{obj.void_reason}）")
    obj.voided_at = None
    obj.voided_by = None
    obj.void_reason = None
    db.commit()
    db.refresh(obj)
    return incident_to_out(obj)


# ---------- 整改跟踪 ----------
@router.get("/rectifications", response_model=list[RectificationOut])
def list_rectifications(status: Optional[str] = None, db: Session = Depends(get_db),
                        user: dict = Depends(get_current_user)):
    q = db.query(Rectification)
    if status:
        q = q.filter(Rectification.status == status)
    return [rect_to_out(r) for r in q.order_by(Rectification.deadline).all()]


@router.post("/rectifications", response_model=RectificationOut, status_code=201)
def create_rectification(data: RectificationCreate, db: Session = Depends(get_db),
                         user: dict = ADMIN_ONLY):
    incident = db.get(Incident, data.incident_id)
    if not incident:
        raise HTTPException(404, "关联的异常工单不存在")
    obj = Rectification(**data.model_dump(), started_at=datetime.now(), status="整改中")
    incident.status = "整改中"
    db.add(obj)
    db.flush()
    log_action(db, user, "下达整改", "rectification", obj.id,
               f"就工单「{incident.title}」下达整改，责任人{obj.responsible}，期限{obj.deadline}")
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)


@router.post("/rectifications/{rect_id}/complete", response_model=RectificationOut)
def complete_rectification(rect_id: int, data: RectificationComplete, db: Session = Depends(get_db),
                           user: dict = ADMIN_ONLY):
    obj = db.get(Rectification, rect_id)
    if not obj:
        raise HTTPException(404, "整改任务不存在")
    if obj.status == "已完成":
        raise HTTPException(400, "该整改已完成")
    obj.status = "已完成"
    obj.completed_at = datetime.now()
    obj.result = data.result
    log_action(db, user, "完成整改", "rectification", obj.id, f"整改完成：{data.result[:80]}")
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)


@router.post("/rectifications/{rect_id}/verify", response_model=RectificationOut)
def verify_rectification(rect_id: int, data: RectificationVerify, db: Session = Depends(get_db),
                         user: dict = ADMIN_ONLY):
    """验收整改任务（验收人强制取当前登录账号）；
    仅当工单下所有整改任务均验收通过后，工单才标记为已整改"""
    obj = db.get(Rectification, rect_id)
    if not obj:
        raise HTTPException(404, "整改任务不存在")
    if obj.status != "已完成":
        raise HTTPException(400, "请先完成整改再验收")
    if obj.verified_at:
        raise HTTPException(400, "该整改任务已验收")
    obj.verifier = user["name"]  # 验收人从登录账号取，不接受客户端传值
    obj.verified_at = datetime.now()
    # 全部整改任务均完成且验收通过，工单才可标记为已整改
    all_verified = all(
        r.status == "已完成" and (r.verified_at is not None or r.id == obj.id)
        for r in obj.incident.rectifications
    )
    if all_verified:
        obj.incident.status = "已整改"
    log_action(db, user, "验收整改", "rectification", obj.id,
               f"验收通过整改#{obj.id}（工单「{obj.incident.title}」）")
    db.commit()
    db.refresh(obj)
    return rect_to_out(obj)
