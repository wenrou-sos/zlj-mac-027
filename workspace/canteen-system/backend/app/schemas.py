"""Pydantic 模型（请求/响应）"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class VoidIn(BaseModel):
    """作废/停用请求：原因必填，留档可查"""
    reason: str


# ---------- 供应商 ----------
class SupplierBase(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    license_no: Optional[str] = None
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None


# ---------- 食材采购 ----------
class PurchaseBase(BaseModel):
    ingredient_name: str
    category: str
    supplier_id: Optional[int] = None
    quantity: float
    unit: str = "kg"
    unit_price: float
    purchase_date: date
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    batch_no: Optional[str] = None
    certificate_no: Optional[str] = None
    purchaser: Optional[str] = None
    inspector: Optional[str] = None
    status: str = "合格"
    storage_location: Optional[str] = None
    remark: Optional[str] = None


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(BaseModel):
    ingredient_name: Optional[str] = None
    category: Optional[str] = None
    supplier_id: Optional[int] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    purchase_date: Optional[date] = None
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    batch_no: Optional[str] = None
    certificate_no: Optional[str] = None
    purchaser: Optional[str] = None
    inspector: Optional[str] = None
    status: Optional[str] = None
    storage_location: Optional[str] = None
    remark: Optional[str] = None


class PurchaseOut(PurchaseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    total_price: float
    supplier_name: Optional[str] = None
    days_to_expiry: Optional[int] = None   # 距过期天数(负数=已过期)
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None


# ---------- 留样 ----------
class SampleBase(BaseModel):
    dish_name: str
    meal_type: str
    sample_time: datetime
    weight_grams: float = 125
    container_no: Optional[str] = None
    fridge_no: Optional[str] = None
    keeper: Optional[str] = None
    remark: Optional[str] = None


class SampleCreate(SampleBase):
    pass


class SampleDispose(BaseModel):
    disposed_by: Optional[str] = None  # 后端强制取当前登录人，客户端传值无效


class SampleOut(SampleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    retention_deadline: datetime
    status: str
    disposed_at: Optional[datetime] = None
    disposed_by: Optional[str] = None
    remaining_hours: Optional[float] = None  # 距到期小时数(负数=已到期)
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None


# ---------- 从业人员 ----------
class StaffBase(BaseModel):
    name: str
    gender: Optional[str] = None
    position: str
    id_card: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    health_cert_no: Optional[str] = None
    cert_issue_date: Optional[date] = None
    cert_expiry_date: Optional[date] = None
    status: str = "在职"


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    position: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    health_cert_no: Optional[str] = None
    cert_issue_date: Optional[date] = None
    cert_expiry_date: Optional[date] = None
    status: Optional[str] = None


class StaffOut(StaffBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cert_days_remaining: Optional[int] = None  # 健康证剩余天数(负数=已过期)
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None


# ---------- 整改 ----------
class RectificationBase(BaseModel):
    measures: str
    responsible: str
    deadline: date


class RectificationCreate(RectificationBase):
    incident_id: int


class RectificationOut(RectificationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    verifier: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    overdue: bool = False  # 是否已逾期


class RectificationComplete(BaseModel):
    result: str


class RectificationVerify(BaseModel):
    verifier: Optional[str] = None  # 后端强制取当前登录人


# ---------- 异常上报 ----------
class IncidentBase(BaseModel):
    title: str
    category: str
    description: Optional[str] = None
    severity: str = "一般"
    reporter: Optional[str] = None


class IncidentCreate(IncidentBase):
    related_type: Optional[str] = None
    related_id: Optional[int] = None


class IncidentOut(IncidentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    status: str
    reported_at: datetime
    closed_at: Optional[datetime] = None
    rectifications: List[RectificationOut] = []
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    voided_by: Optional[str] = None


# ---------- 预警 ----------
class Alert(BaseModel):
    type: str          # sample/cert/purchase/rectification
    level: str         # danger/warning/info
    title: str
    description: str
    related_id: Optional[int] = None
