"""供应商 CRUD"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, ROLE_PURCHASER, get_current_user, require_roles
from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierOut
from ..services import log_action

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])

SUPPLIER_ROLES = (ROLE_ADMIN, ROLE_PURCHASER)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return db.query(Supplier).order_by(Supplier.id).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*SUPPLIER_ROLES))):
    if db.query(Supplier).filter(Supplier.name == data.name).first():
        raise HTTPException(400, "供应商名称已存在")
    obj = Supplier(**data.model_dump())
    db.add(obj)
    db.flush()
    log_action(db, user, "供应商登记", "supplier", obj.id, f"登记供应商「{obj.name}」")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*SUPPLIER_ROLES))):
    obj = db.get(Supplier, supplier_id)
    if not obj:
        raise HTTPException(404, "供应商不存在")
    if obj.purchases:
        raise HTTPException(400, "该供应商存在采购记录，无法删除")
    log_action(db, user, "供应商删除", "supplier", obj.id, f"删除供应商「{obj.name}」")
    db.delete(obj)
    db.commit()
