"""从业人员健康证管理"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Staff
from ..schemas import StaffCreate, StaffOut, StaffUpdate

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
    db: Session = Depends(get_db),
):
    q = db.query(Staff)
    if status:
        q = q.filter(Staff.status == status)
    if position:
        q = q.filter(Staff.position == position)
    if keyword:
        q = q.filter(Staff.name.contains(keyword))
    return [to_out(s) for s in q.order_by(Staff.cert_expiry_date).all()]


@router.post("", response_model=StaffOut, status_code=201)
def create_staff(data: StaffCreate, db: Session = Depends(get_db)):
    obj = Staff(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.put("/{staff_id}", response_model=StaffOut)
def update_staff(staff_id: int, data: StaffUpdate, db: Session = Depends(get_db)):
    obj = db.get(Staff, staff_id)
    if not obj:
        raise HTTPException(404, "人员不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    obj = db.get(Staff, staff_id)
    if not obj:
        raise HTTPException(404, "人员不存在")
    db.delete(obj)
    db.commit()
