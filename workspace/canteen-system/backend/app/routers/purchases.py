"""食材采购 CRUD + 筛选"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, ROLE_PURCHASER, get_current_user, require_roles
from ..database import get_db
from ..models import Purchase
from ..schemas import PurchaseCreate, PurchaseOut, PurchaseUpdate
from ..services import log_action

router = APIRouter(prefix="/api/purchases", tags=["食材采购"])

# 采购维护：食品安全管理员、采购员
PURCHASE_ROLES = (ROLE_ADMIN, ROLE_PURCHASER)


def to_out(p: Purchase) -> dict:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["supplier_name"] = p.supplier.name if p.supplier else None
    d["days_to_expiry"] = (p.expiry_date - date.today()).days if p.expiry_date else None
    return d


@router.get("", response_model=list[PurchaseOut])
def list_purchases(
    category: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(Purchase)
    if category:
        q = q.filter(Purchase.category == category)
    if status:
        q = q.filter(Purchase.status == status)
    if keyword:
        q = q.filter(Purchase.ingredient_name.contains(keyword))
    if date_from:
        q = q.filter(Purchase.purchase_date >= date_from)
    if date_to:
        q = q.filter(Purchase.purchase_date <= date_to)
    return [to_out(p) for p in q.order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).all()]


@router.post("", response_model=PurchaseOut, status_code=201)
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*PURCHASE_ROLES))):
    obj = Purchase(**data.model_dump(), total_price=round(data.quantity * data.unit_price, 2))
    db.add(obj)
    db.flush()
    log_action(db, user, "采购登记", "purchase", obj.id,
               f"登记采购「{obj.ingredient_name}」{obj.quantity}{obj.unit}，¥{obj.total_price}")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.put("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(purchase_id: int, data: PurchaseUpdate, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*PURCHASE_ROLES))):
    obj = db.get(Purchase, purchase_id)
    if not obj:
        raise HTTPException(404, "采购记录不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.total_price = round(obj.quantity * obj.unit_price, 2)
    log_action(db, user, "采购修改", "purchase", obj.id,
               f"修改采购「{obj.ingredient_name}」记录")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*PURCHASE_ROLES))):
    obj = db.get(Purchase, purchase_id)
    if not obj:
        raise HTTPException(404, "采购记录不存在")
    log_action(db, user, "采购作废", "purchase", obj.id,
               f"作废采购「{obj.ingredient_name}」{obj.quantity}{obj.unit}记录")
    db.delete(obj)
    db.commit()
