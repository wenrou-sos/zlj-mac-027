"""供应商管理（删除改为归档式停用）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, ROLE_PURCHASER, get_current_user, require_roles
from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierOut, VoidIn
from ..services import log_action

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])

SUPPLIER_ROLES = (ROLE_ADMIN, ROLE_PURCHASER)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(view: str = "valid", db: Session = Depends(get_db),
                   user: dict = Depends(get_current_user)):
    """view: valid有效(默认)/voided已停用/all全部"""
    q = db.query(Supplier)
    if view == "valid":
        q = q.filter(Supplier.voided_at.is_(None))
    elif view == "voided":
        q = q.filter(Supplier.voided_at.isnot(None))
    return q.order_by(Supplier.id).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db),
                    user: dict = Depends(require_roles(*SUPPLIER_ROLES))):
    if db.query(Supplier).filter(Supplier.name == data.name, Supplier.voided_at.is_(None)).first():
        raise HTTPException(400, "供应商名称已存在")
    obj = Supplier(**data.model_dump())
    db.add(obj)
    db.flush()
    log_action(db, user, "供应商登记", "supplier", obj.id, f"登记供应商「{obj.name}」")
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{supplier_id}/void", response_model=SupplierOut)
def void_supplier(supplier_id: int, data: VoidIn, db: Session = Depends(get_db),
                  user: dict = Depends(require_roles(*SUPPLIER_ROLES))):
    """停用供应商：原记录与历史采购关联保留可查"""
    obj = db.get(Supplier, supplier_id)
    if not obj:
        raise HTTPException(404, "供应商不存在")
    if obj.voided_at:
        raise HTTPException(400, "该供应商已停用")
    if not data.reason.strip():
        raise HTTPException(400, "请填写停用原因")
    obj.voided_at = datetime.now()
    obj.voided_by = user["name"]
    obj.void_reason = data.reason.strip()
    log_action(db, user, "供应商停用", "supplier", obj.id,
               f"停用供应商「{obj.name}」，原因：{obj.void_reason}")
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{supplier_id}/restore", response_model=SupplierOut)
def restore_supplier(supplier_id: int, db: Session = Depends(get_db),
                     user: dict = Depends(require_roles(ROLE_ADMIN))):
    """恢复误停用的供应商（仅管理员）"""
    obj = db.get(Supplier, supplier_id)
    if not obj:
        raise HTTPException(404, "供应商不存在")
    if not obj.voided_at:
        raise HTTPException(400, "该供应商未停用")
    log_action(db, user, "供应商恢复", "supplier", obj.id,
               f"恢复供应商「{obj.name}」（原停用原因：{obj.void_reason}）")
    obj.voided_at = None
    obj.voided_by = None
    obj.void_reason = None
    db.commit()
    db.refresh(obj)
    return obj
