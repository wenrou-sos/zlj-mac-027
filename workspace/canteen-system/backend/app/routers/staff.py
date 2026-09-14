"""从业人员健康证管理（删除改为归档式作废）"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, get_current_user, require_roles
from ..database import get_db
from ..models import Staff
from ..schemas import StaffCreate, StaffOut, StaffUpdate, VoidIn
from ..services import log_action

router = APIRouter(prefix="/api/staff", tags=["从业人员"])


def to_out(s: Staff) -> dict:
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    d["cert_days_remaining"] = (s.cert_expiry_date - date.today()).days if s.cert_expiry_date else None
    return d


@router.get("", response_model=list[StaffOut])
def list_staff(
    status: Optional[str] = None,
    position: Optional[str] = None,
    keyword: Optional[str] = None,
    view: str = "valid",  # valid有效(默认)/voided已作废/all全部
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(Staff)
    if view == "valid":
        q = q.filter(Staff.voided_at.is_(None))
    elif view == "voided":
        q = q.filter(Staff.voided_at.isnot(None))
    if status:
        q = q.filter(Staff.status == status)
    if position:
        q = q.filter(Staff.position == position)
    if keyword:
        q = q.filter(Staff.name.contains(keyword))
    return [to_out(s) for s in q.order_by(Staff.cert_expiry_date).all()]


@router.post("", response_model=StaffOut, status_code=201)
def create_staff(data: StaffCreate, db: Session = Depends(get_db),
                 user: dict = Depends(require_roles(ROLE_ADMIN))):
    obj = Staff(**data.model_dump())
    db.add(obj)
    db.flush()
    log_action(db, user, "人员登记", "staff", obj.id, f"登记从业人员「{obj.name}」（{obj.position}）")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.put("/{staff_id}", response_model=StaffOut)
def update_staff(staff_id: int, data: StaffUpdate, db: Session = Depends(get_db),
                 user: dict = Depends(require_roles(ROLE_ADMIN))):
    obj = db.get(Staff, staff_id)
    if not obj:
        raise HTTPException(404, "人员不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    log_action(db, user, "人员修改", "staff", obj.id, f"修改从业人员「{obj.name}」信息")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{staff_id}/void", response_model=StaffOut)
def void_staff(staff_id: int, data: VoidIn, db: Session = Depends(get_db),
               user: dict = Depends(require_roles(ROLE_ADMIN))):
    """作废人员档案（如重复建档）：原记录保留可查"""
    obj = db.get(Staff, staff_id)
    if not obj:
        raise HTTPException(404, "人员不存在")
    if obj.voided_at:
        raise HTTPException(400, "该档案已作废")
    if not data.reason.strip():
        raise HTTPException(400, "请填写作废原因")
    obj.voided_at = datetime.now()
    obj.voided_by = user["name"]
    obj.void_reason = data.reason.strip()
    log_action(db, user, "人员作废", "staff", obj.id,
               f"作废人员档案「{obj.name}」（{obj.position}），原因：{obj.void_reason}")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{staff_id}/restore", response_model=StaffOut)
def restore_staff(staff_id: int, db: Session = Depends(get_db),
                  user: dict = Depends(require_roles(ROLE_ADMIN))):
    """恢复误作废的人员档案"""
    obj = db.get(Staff, staff_id)
    if not obj:
        raise HTTPException(404, "人员不存在")
    if not obj.voided_at:
        raise HTTPException(400, "该档案未作废")
    log_action(db, user, "人员恢复", "staff", obj.id,
               f"恢复人员档案「{obj.name}」（原作废原因：{obj.void_reason}）")
    obj.voided_at = None
    obj.voided_by = None
    obj.void_reason = None
    db.commit()
    db.refresh(obj)
    return to_out(obj)
