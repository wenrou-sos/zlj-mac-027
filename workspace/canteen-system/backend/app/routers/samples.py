"""留样记录：登记、查询、销毁；自动计算48小时到期时间与倒计时。
留样登记/销毁：食品安全管理员、留样人；销毁人强制取当前登录账号。"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, ROLE_KEEPER, get_current_user, require_roles
from ..database import get_db
from ..models import Sample
from ..schemas import SampleCreate, SampleDispose, SampleOut, VoidIn
from ..services import SAMPLE_RETENTION_HOURS, log_action

router = APIRouter(prefix="/api/samples", tags=["留样记录"])

SAMPLE_ROLES = (ROLE_ADMIN, ROLE_KEEPER)


def to_out(s: Sample) -> dict:
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    d["remaining_hours"] = round((s.retention_deadline - datetime.now()).total_seconds() / 3600, 1)
    return d


@router.get("", response_model=list[SampleOut])
def list_samples(
    meal_type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    view: str = "valid",  # valid有效(默认)/voided已作废/all全部
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(Sample)
    if view == "valid":
        q = q.filter(Sample.voided_at.is_(None))
    elif view == "voided":
        q = q.filter(Sample.voided_at.isnot(None))
    if meal_type:
        q = q.filter(Sample.meal_type == meal_type)
    if status:
        q = q.filter(Sample.status == status)
    if keyword:
        q = q.filter(Sample.dish_name.contains(keyword))
    return [to_out(s) for s in q.order_by(Sample.sample_time.desc()).all()]


@router.post("", response_model=SampleOut, status_code=201)
def create_sample(data: SampleCreate, db: Session = Depends(get_db),
                  user: dict = Depends(require_roles(*SAMPLE_ROLES))):
    if data.sample_time > datetime.now():
        raise HTTPException(400, "留样时间不能晚于当前时间")
    if data.weight_grams < 125:
        raise HTTPException(400, "留样重量不得少于125克")
    obj = Sample(
        **data.model_dump(),
        retention_deadline=data.sample_time + timedelta(hours=SAMPLE_RETENTION_HOURS),
    )
    db.add(obj)
    db.flush()
    log_action(db, user, "留样登记", "sample", obj.id,
               f"登记{obj.meal_type}留样「{obj.dish_name}」{obj.weight_grams}g")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{sample_id}/dispose", response_model=SampleOut)
def dispose_sample(sample_id: int, data: SampleDispose, db: Session = Depends(get_db),
                   user: dict = Depends(require_roles(*SAMPLE_ROLES))):
    """留样到期销毁登记（未满48小时保存期不得销毁）；销毁人强制取当前登录账号"""
    obj = db.get(Sample, sample_id)
    if not obj:
        raise HTTPException(404, "留样记录不存在")
    if obj.status != "留样中":
        raise HTTPException(400, f"当前状态为「{obj.status}」，无法销毁")
    if datetime.now() < obj.retention_deadline:
        raise HTTPException(
            400,
            f"留样未满48小时保存期（{obj.retention_deadline.strftime('%m-%d %H:%M')} 到期），暂不能销毁",
        )
    obj.status = "已销毁"
    obj.disposed_at = datetime.now()
    obj.disposed_by = user["name"]  # 销毁人从登录账号取，不接受客户端传值
    log_action(db, user, "留样销毁", "sample", obj.id,
               f"销毁{obj.meal_type}留样「{obj.dish_name}」")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{sample_id}/void", response_model=SampleOut)
def void_sample(sample_id: int, data: VoidIn, db: Session = Depends(get_db),
                user: dict = Depends(require_roles(ROLE_ADMIN))):
    """作废留样记录（如登记错误）：原记录保留可查，物理删除不提供"""
    obj = db.get(Sample, sample_id)
    if not obj:
        raise HTTPException(404, "留样记录不存在")
    if obj.voided_at:
        raise HTTPException(400, "该记录已作废")
    if not data.reason.strip():
        raise HTTPException(400, "请填写作废原因")
    obj.voided_at = datetime.now()
    obj.voided_by = user["name"]
    obj.void_reason = data.reason.strip()
    log_action(db, user, "留样作废", "sample", obj.id,
               f"作废{obj.meal_type}留样「{obj.dish_name}」，原因：{obj.void_reason}")
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{sample_id}/restore", response_model=SampleOut)
def restore_sample(sample_id: int, db: Session = Depends(get_db),
                   user: dict = Depends(require_roles(ROLE_ADMIN))):
    """恢复误作废的留样记录"""
    obj = db.get(Sample, sample_id)
    if not obj:
        raise HTTPException(404, "留样记录不存在")
    if not obj.voided_at:
        raise HTTPException(400, "该记录未作废")
    log_action(db, user, "留样恢复", "sample", obj.id,
               f"恢复{obj.meal_type}留样「{obj.dish_name}」（原作废原因：{obj.void_reason}）")
    obj.voided_at = None
    obj.voided_by = None
    obj.void_reason = None
    db.commit()
    db.refresh(obj)
    return to_out(obj)
