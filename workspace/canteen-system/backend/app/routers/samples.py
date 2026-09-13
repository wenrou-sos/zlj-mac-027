"""留样记录：登记、查询、销毁；自动计算48小时到期时间与倒计时"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Sample
from ..schemas import SampleCreate, SampleDispose, SampleOut
from ..services import SAMPLE_RETENTION_HOURS

router = APIRouter(prefix="/api/samples", tags=["留样记录"])


def to_out(s: Sample) -> dict:
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    d["remaining_hours"] = round((s.retention_deadline - datetime.now()).total_seconds() / 3600, 1)
    return d


@router.get("", response_model=list[SampleOut])
def list_samples(
    meal_type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Sample)
    if meal_type:
        q = q.filter(Sample.meal_type == meal_type)
    if status:
        q = q.filter(Sample.status == status)
    if keyword:
        q = q.filter(Sample.dish_name.contains(keyword))
    return [to_out(s) for s in q.order_by(Sample.sample_time.desc()).all()]


@router.post("", response_model=SampleOut, status_code=201)
def create_sample(data: SampleCreate, db: Session = Depends(get_db)):
    if data.weight_grams < 125:
        raise HTTPException(400, "留样重量不得少于125克")
    obj = Sample(
        **data.model_dump(),
        retention_deadline=data.sample_time + timedelta(hours=SAMPLE_RETENTION_HOURS),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.post("/{sample_id}/dispose", response_model=SampleOut)
def dispose_sample(sample_id: int, data: SampleDispose, db: Session = Depends(get_db)):
    """留样到期销毁登记"""
    obj = db.get(Sample, sample_id)
    if not obj:
        raise HTTPException(404, "留样记录不存在")
    if obj.status != "留样中":
        raise HTTPException(400, f"当前状态为「{obj.status}」，无法销毁")
    obj.status = "已销毁"
    obj.disposed_at = datetime.now()
    obj.disposed_by = data.disposed_by
    db.commit()
    db.refresh(obj)
    return to_out(obj)


@router.delete("/{sample_id}", status_code=204)
def delete_sample(sample_id: int, db: Session = Depends(get_db)):
    obj = db.get(Sample, sample_id)
    if not obj:
        raise HTTPException(404, "留样记录不存在")
    db.delete(obj)
    db.commit()
