"""自动巡检调度器：随 FastAPI 进程运行的 asyncio 后台任务。

每 TICK_SECONDS 秒检查一次：若当前时间已过某个配置的运行时刻，
且该时刻之后还没有自动运行记录，则补跑/到点跑一次。
同一时刻槽位只跑一次（以 inspection_runs 表为准），服务重启不会重复执行。
"""
import asyncio
from datetime import datetime

from .database import SessionLocal
from .models import InspectionRun
from .services import execute_inspection, get_inspection_config, latest_scheduled_occurrence

TICK_SECONDS = 30
_task: asyncio.Task | None = None


async def _loop():
    while True:
        try:
            db = SessionLocal()
            try:
                cfg = get_inspection_config(db)
                if cfg["enabled"] and cfg["run_times"]:
                    now = datetime.now()
                    due = latest_scheduled_occurrence(cfg["run_times"], now)
                    last_auto = (db.query(InspectionRun)
                                 .filter(InspectionRun.trigger == "自动")
                                 .order_by(InspectionRun.started_at.desc())
                                 .first())
                    if due and (last_auto is None or last_auto.started_at < due):
                        run, result = execute_inspection(db, "自动")
                        print(f"🕐 自动巡检完成 @ {now:%H:%M}，新开 {run.created_count} 单，"
                              f"自动关闭 {result['closed']} 单")
            finally:
                db.close()
        except Exception as exc:
            print(f"⚠️ 自动巡检调度异常: {exc}")
        await asyncio.sleep(TICK_SECONDS)


def start_scheduler():
    global _task
    if _task is None:
        _task = asyncio.create_task(_loop())


def stop_scheduler():
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
