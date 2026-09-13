"""仪表盘统计 + 预警聚合 + 系统巡检"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Incident, Purchase, Rectification, Sample, Staff
from ..schemas import Alert
from ..services import CERT_WARN_DAYS, SAMPLE_WARN_HOURS, compute_alerts, run_inspection

router = APIRouter(prefix="/api", tags=["仪表盘"])


@router.get("/alerts", response_model=list[Alert])
def get_alerts(db: Session = Depends(get_db)):
    return compute_alerts(db)


@router.post("/inspection/run")
def inspection(db: Session = Depends(get_db)):
    """手动触发系统巡检：自动生成异常工单（健康证过期/食材过期/留样超期/整改逾期）"""
    return run_inspection(db)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.now()
    today = date.today()
    month_start = today.replace(day=1)

    # ---- 核心指标 ----
    active_samples = db.query(Sample).filter(Sample.status == "留样中").all()
    expiring_soon = sum(1 for s in active_samples
                        if 0 <= (s.retention_deadline - now).total_seconds() / 3600 <= SAMPLE_WARN_HOURS)
    pending_dispose = sum(1 for s in active_samples if s.retention_deadline < now)
    today_samples = sum(1 for s in active_samples if s.sample_time.date() == today)

    staff_active = db.query(Staff).filter(Staff.status == "在职").all()
    cert_expiring = sum(1 for s in staff_active
                        if s.cert_expiry_date and 0 <= (s.cert_expiry_date - today).days <= CERT_WARN_DAYS)
    cert_expired = sum(1 for s in staff_active
                       if s.cert_expiry_date and s.cert_expiry_date < today)

    open_incidents = db.query(Incident).filter(Incident.status.in_(["待处理", "整改中"])).count()
    overdue_rects = db.query(Rectification).filter(
        Rectification.deadline < today,
        Rectification.status.in_(["待整改", "整改中", "已逾期"]),
    ).count()

    month_amount = db.query(func.coalesce(func.sum(Purchase.total_price), 0)).filter(
        Purchase.purchase_date >= month_start).scalar()

    # ---- 图表数据 ----
    # 采购分类占比（近30天）
    cat_rows = db.query(Purchase.category, func.sum(Purchase.total_price)).filter(
        Purchase.purchase_date >= today - timedelta(days=30),
    ).group_by(Purchase.category).all()
    purchase_by_category = [{"category": c, "amount": round(a or 0, 2)} for c, a in cat_rows]

    # 近7日采购金额
    purchase_last_7_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        amt = db.query(func.coalesce(func.sum(Purchase.total_price), 0)).filter(
            Purchase.purchase_date == d).scalar()
        purchase_last_7_days.append({"date": d.strftime("%m-%d"), "amount": round(amt, 2)})

    # 异常分类分布
    inc_rows = db.query(Incident.category, func.count(Incident.id)).group_by(Incident.category).all()
    incident_by_category = [{"category": c, "count": n} for c, n in inc_rows]

    return {
        "stats": {
            "today_samples": today_samples,
            "active_samples": len(active_samples),
            "expiring_samples": expiring_soon,
            "pending_dispose": pending_dispose,
            "staff_total": len(staff_active),
            "cert_expiring": cert_expiring,
            "cert_expired": cert_expired,
            "open_incidents": open_incidents,
            "overdue_rectifications": overdue_rects,
            "month_purchase_amount": round(month_amount, 2),
        },
        "purchase_by_category": purchase_by_category,
        "purchase_last_7_days": purchase_last_7_days,
        "incident_by_category": incident_by_category,
        "alerts": compute_alerts(db),
    }
