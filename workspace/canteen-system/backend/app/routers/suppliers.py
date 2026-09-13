"""供应商 CRUD"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierOut

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.id).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.name == data.name).first():
        raise HTTPException(400, "供应商名称已存在")
    obj = Supplier(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    obj = db.get(Supplier, supplier_id)
    if not obj:
        raise HTTPException(404, "供应商不存在")
    if obj.purchases:
        raise HTTPException(400, "该供应商存在采购记录，无法删除")
    db.delete(obj)
    db.commit()
