"""应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine, run_migrations
from .routers import auth, dashboard, incidents, inspection, purchases, samples, staff, suppliers
from .scheduler import start_scheduler, stop_scheduler
from .seed import seed

app = FastAPI(title="学校食堂食品安全管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, dashboard.router, suppliers.router, purchases.router,
          samples.router, staff.router, incidents.router, inspection.router):
    app.include_router(r)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.on_event("startup")
async def startup_scheduler():
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_scheduler():
    stop_scheduler()


@app.get("/api/health")
def health():
    return {"status": "ok"}
