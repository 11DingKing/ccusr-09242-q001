from sqlalchemy import create_engine, inspect, text
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


def ensure_schema_upgrades():
    """对已存在的数据库做增量列迁移（create_all 不会修改已有表）。

    状态日志表新增受控回退相关列；SQLite 不支持 ADD CONSTRAINT，
    幂等唯一约束通过 CREATE UNIQUE INDEX IF NOT EXISTS 补齐。
    """
    inspector = inspect(engine)
    if "project_status_logs" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("project_status_logs")}
    with engine.begin() as conn:
        if "action" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE project_status_logs "
                    "ADD COLUMN action VARCHAR(32) NOT NULL DEFAULT 'transition'"
                )
            )
        if "request_id" not in existing:
            conn.execute(
                text("ALTER TABLE project_status_logs ADD COLUMN request_id VARCHAR(64)")
            )
        if "affected_records" not in existing:
            conn.execute(
                text("ALTER TABLE project_status_logs ADD COLUMN affected_records TEXT")
            )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_status_logs_project_request "
                "ON project_status_logs (project_id, request_id)"
            )
        )
