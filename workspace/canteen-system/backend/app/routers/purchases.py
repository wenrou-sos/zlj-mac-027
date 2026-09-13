"""食材采购 CRUD + 筛选"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Purchase
from ..schemas import PurchaseCreate, PurchaseOut, PurchaseUpdate

router = APIRouter(prefix="/api/purchases", tags=["食材采购"])


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
def create_purchase(data: PurchaseCreate, db: Session = Depends(get_db)):
    obj = Purchase(**data.model_dump(), total_price=round(data.quantity * data.unit_price, 2))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.put("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(purchase_id: int, data: PurchaseUpdate, db: Session = Depends(get_db)):
    obj = db.get(Purchase, purchase_id)
    if not obj:
        raise HTTPException(404, "采购记录不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.total_price = round(obj.quantity * obj.unit_price, 2)
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.delete("/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    obj = db.get(Purchase, purchase_id)
    if not obj:
        raise HTTPException(404, "采购记录不存在")
    db.delete(obj)
    db.commit()
