from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 已上线表的新增列：(表, 列, ALTER 片段)
# SQLAlchemy 的 JSON 在 SQLite 下以 TEXT 存储。
_ADDED_COLUMNS = [
    (
        "project_status_logs",
        "log_kind",
        "ALTER TABLE project_status_logs ADD COLUMN log_kind VARCHAR(16) "
        "NOT NULL DEFAULT 'normal'",
    ),
    (
        "project_status_logs",
        "request_id",
        "ALTER TABLE project_status_logs ADD COLUMN request_id VARCHAR(64)",
    ),
    (
        "project_status_logs",
        "affected_records",
        "ALTER TABLE project_status_logs ADD COLUMN affected_records TEXT",
    ),
]


def run_lightweight_migrations(bind_engine) -> None:
    """对旧库补齐新列；全新库或已迁移过的库均为幂等空操作。"""
    with bind_engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            existing = {
                row[1]
                for row in conn.exec_driver_sql(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            if not existing:
                # 表尚不存在，create_all 会按最新模型建表
                continue
            if column not in existing:
                conn.exec_driver_sql(ddl)
