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


# 归档式作废字段（各业务表统一）
VOID_COLUMNS = {
    "voided_at": "TIMESTAMP",
    "void_reason": "VARCHAR(200)",
    "voided_by": "VARCHAR(50)",
}
VOID_TABLES = ("samples", "purchases", "staff", "suppliers", "incidents")


def run_migrations():
    """轻量迁移：为已存在的数据库补充新增列（create_all 不会改已有表）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in VOID_TABLES:
            if table not in existing_tables:
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table)}
            for col_name, col_type in VOID_COLUMNS.items():
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                    print(f"  迁移：{table} 新增列 {col_name}")
