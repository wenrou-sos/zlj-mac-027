"""业务逻辑：预警计算、系统巡检（自动生成异常工单）"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from .models import Incident, Purchase, Rectification, Sample, Staff

# 预警阈值常量
SAMPLE_RETENTION_HOURS = 48      # 留样保存时长(小时)
SAMPLE_WARN_HOURS = 2            # 留样到期前提醒(小时)
CERT_WARN_DAYS = 30              # 健康证到期前提醒(天)
PURCHASE_WARN_DAYS = 3           # 食材临期提醒(天)


def compute_alerts(db: Session) -> list[dict]:
    """汇总当前所有预警信息"""
    now = datetime.now()
    today = date.today()
    alerts: list[dict] = []

    # 1. 留样预警
    active_samples = db.query(Sample).filter(Sample.status == "留样中").all()
    for s in active_samples:
        remaining = (s.retention_deadline - now).total_seconds() / 3600
        if remaining < 0:
            alerts.append({
                "type": "sample", "level": "danger", "related_id": s.id,
                "title": f"留样超期未销毁：{s.dish_name}",
                "description": f"{s.meal_type}留样已于 {s.retention_deadline.strftime('%m-%d %H:%M')} 满48小时，请及时销毁并登记",
            })
        elif remaining <= SAMPLE_WARN_HOURS:
            alerts.append({
                "type": "sample", "level": "warning", "related_id": s.id,
                "title": f"留样即将到期：{s.dish_name}",
                "description": f"{s.meal_type}留样将于 {s.retention_deadline.strftime('%m-%d %H:%M')} 到期（剩余{remaining:.1f}小时）",
            })

    # 2. 健康证预警
    staff_list = db.query(Staff).filter(Staff.status == "在职").all()
    for st in staff_list:
        if not st.cert_expiry_date:
            continue
        days = (st.cert_expiry_date - today).days
        if days < 0:
            alerts.append({
                "type": "cert", "level": "danger", "related_id": st.id,
                "title": f"健康证已过期：{st.name}",
                "description": f"{st.position} {st.name} 的健康证已于 {st.cert_expiry_date} 过期{-days}天，须立即离岗并补办",
            })
        elif days <= CERT_WARN_DAYS:
            alerts.append({
                "type": "cert", "level": "warning", "related_id": st.id,
                "title": f"健康证即将到期：{st.name}",
                "description": f"{st.position} {st.name} 的健康证将于 {st.cert_expiry_date} 到期（剩余{days}天），请安排体检换证",
            })

    # 3. 食材保质期预警
    purchases = db.query(Purchase).filter(Purchase.status != "不合格", Purchase.expiry_date.isnot(None)).all()
    for p in purchases:
        days = (p.expiry_date - today).days
        if days < 0:
            alerts.append({
                "type": "purchase", "level": "danger", "related_id": p.id,
                "title": f"食材已过期：{p.ingredient_name}",
                "description": f"批次{p.batch_no or '-'}已于 {p.expiry_date} 过期{-days}天，请立即封存销毁",
            })
        elif days <= PURCHASE_WARN_DAYS:
            alerts.append({
                "type": "purchase", "level": "warning", "related_id": p.id,
                "title": f"食材临期：{p.ingredient_name}",
                "description": f"批次{p.batch_no or '-'}将于 {p.expiry_date} 到期（剩余{days}天），请优先使用",
            })

    # 4. 整改逾期预警
    rects = db.query(Rectification).filter(Rectification.status.in_(["待整改", "整改中", "已逾期"])).all()
    for r in rects:
        if r.deadline < today:
            alerts.append({
                "type": "rectification", "level": "danger", "related_id": r.id,
                "title": f"整改已逾期：{r.measures[:20]}...",
                "description": f"责任人 {r.responsible}，整改期限 {r.deadline}，已逾期{(today - r.deadline).days}天",
            })

    level_order = {"danger": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: level_order.get(a["level"], 3))
    return alerts


def run_inspection(db: Session) -> dict:
    """系统巡检：扫描问题并自动生成异常工单（已存在未关闭工单的则跳过）。
    返回新生成的工单摘要。"""
    today = date.today()
    created: list[Incident] = []

    def has_open_incident(related_type: str, related_id: int) -> bool:
        return db.query(Incident).filter(
            Incident.related_type == related_type,
            Incident.related_id == related_id,
            Incident.status.in_(["待处理", "整改中"]),
        ).first() is not None

    # 1. 健康证过期 -> 自动生成工单
    for st in db.query(Staff).filter(Staff.status == "在职").all():
        if st.cert_expiry_date and st.cert_expiry_date < today and not has_open_incident("staff", st.id):
            inc = Incident(
                title=f"健康证过期：{st.name}",
                category="健康证异常",
                description=f"系统巡检发现：{st.position} {st.name} 的健康证（{st.health_cert_no or '无证号'}）"
                            f"已于 {st.cert_expiry_date} 过期，违反《食品安全法》第四十五条，须立即调离岗位并补办。",
                severity="严重", reporter="系统", source="系统巡检",
                related_type="staff", related_id=st.id,
            )
            db.add(inc)
            created.append(inc)

    # 2. 食材过期 -> 自动生成工单
    for p in db.query(Purchase).filter(Purchase.status != "不合格", Purchase.expiry_date.isnot(None)).all():
        if p.expiry_date < today and not has_open_incident("purchase", p.id):
            inc = Incident(
                title=f"食材过期：{p.ingredient_name}",
                category="食材异常",
                description=f"系统巡检发现：{p.ingredient_name}（批次{p.batch_no or '-'}，存放于{p.storage_location or '-'}）"
                            f"已于 {p.expiry_date} 过期，请立即封存、销毁并核查库存。",
                severity="较重", reporter="系统", source="系统巡检",
                related_type="purchase", related_id=p.id,
            )
            db.add(inc)
            created.append(inc)

    # 3. 留样超期未销毁 -> 自动生成工单（超过48小时截止仍未销毁即触发）
    now = datetime.now()
    for s in db.query(Sample).filter(Sample.status == "留样中", Sample.retention_deadline < now).all():
        if not has_open_incident("sample", s.id):
            inc = Incident(
                title=f"留样超期未处理：{s.dish_name}",
                category="留样异常",
                description=f"系统巡检发现：{s.meal_type}留样「{s.dish_name}」（留样人{s.keeper or '-'}）"
                            f"已于 {s.retention_deadline.strftime('%Y-%m-%d %H:%M')} 满48小时，至今未销毁登记。",
                severity="一般", reporter="系统", source="系统巡检",
                related_type="sample", related_id=s.id,
            )
            db.add(inc)
            created.append(inc)

    # 4. 整改逾期 -> 更新状态并生成工单
    for r in db.query(Rectification).filter(Rectification.status.in_(["待整改", "整改中", "已逾期"])).all():
        if r.deadline < today:
            if r.status != "已逾期":
                r.status = "已逾期"
            if not has_open_incident("rectification", r.id):
                inc = Incident(
                    title=f"整改逾期未完成（工单#{r.id}）",
                    category="其他",
                    description=f"系统巡检发现：整改任务「{r.measures[:50]}」（责任人{r.responsible}）"
                                f"期限 {r.deadline} 已逾期{(today - r.deadline).days}天仍未完成。",
                    severity="较重", reporter="系统", source="系统巡检",
                    related_type="rectification", related_id=r.id,
                )
                db.add(inc)
                created.append(inc)

    db.commit()
    return {"created": len(created), "items": [{"id": i.id, "title": i.title} for i in created]}
