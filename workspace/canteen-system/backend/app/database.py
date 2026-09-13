"""数据库连接配置。

默认使用本地 SQLite 文件库，开箱即用；
生产环境设置环境变量 DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/canteen
即可无缝切换到 PostgreSQL（见根目录 docker-compose.yml）。
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./canteen.db")

# SQLite 需要 check_same_thread=False；PostgreSQL 不需要该参数
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
