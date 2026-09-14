"""巡检：状态查询、配置修改、手动触发"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import ROLE_ADMIN, get_current_user, require_roles
from ..database import get_db
from ..models import Incident, InspectionRun
from ..services import (STALE_HOURS, compute_next_run, execute_inspection,
                        get_inspection_config, inspection_stale, last_successful_run,
                        log_action, save_inspection_config)

router = APIRouter(prefix="/api/inspection", tags=["巡检"])

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class InspectionConfigIn(BaseModel):
    enabled: bool
    run_times: list[str]  # 每日运行时刻，格式 HH:MM


def run_to_dict(r: InspectionRun) -> dict:
    return {
        "id": r.id,
        "trigger": r.trigger,
        "started_at": r.started_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "status": r.status,
        "created_count": r.created_count,
        "error": r.error,
    }


@router.get("/status")
def inspection_status(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """巡检运行状态：配置、最近一次运行、未处理工单数、是否超时未成功"""
    cfg = get_inspection_config(db)
    last_run = db.query(InspectionRun).order_by(InspectionRun.started_at.desc()).first()
    last_ok = last_successful_run(db)
    open_incidents = db.query(Incident).filter(Incident.status.in_(["待处理", "整改中"])).count()
    next_run = compute_next_run(cfg["run_times"], datetime.now()) if cfg["enabled"] else None
    return {
        "enabled": cfg["enabled"],
        "run_times": cfg["run_times"],
        "stale_after_hours": STALE_HOURS,
        "stale": inspection_stale(db),
        "last_run": run_to_dict(last_run) if last_run else None,
        "last_success_at": last_ok.finished_at.isoformat() if last_ok else None,
        "next_run_at": next_run.isoformat() if next_run else None,
        "open_incidents": open_incidents,
    }


@router.put("/config")
def update_config(data: InspectionConfigIn, db: Session = Depends(get_db),
                  user: dict = Depends(require_roles(ROLE_ADMIN))):
    times = sorted(set(t.strip() for t in data.run_times if t.strip()))
    for t in times:
        if not TIME_RE.match(t):
            raise HTTPException(400, f"运行时刻格式错误：{t}（应为 HH:MM，如 07:00）")
    if data.enabled and not times:
        raise HTTPException(400, "启用自动巡检时至少需要一个运行时刻")
    save_inspection_config(db, data.enabled, times)
    log_action(db, user, "修改巡检配置", "inspection_config", None,
               f"{'启用' if data.enabled else '停用'}自动巡检，时刻：{'/'.join(times) or '无'}")
    db.commit()
    return inspection_status(db, user)


@router.post("/run")
def manual_run(db: Session = Depends(get_db),
               user: dict = Depends(require_roles(ROLE_ADMIN))):
    """手动触发一次巡检（同样落库运行记录）"""
    run, result = execute_inspection(db, "手动")
    if run.status != "成功":
        raise HTTPException(500, f"巡检执行失败：{run.error}")
    log_action(db, user, "手动巡检", "inspection_run", run.id,
               f"新开 {result['created']} 单，自动关闭 {result['closed']} 单")
    db.commit()
    return result
