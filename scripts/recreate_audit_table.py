import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.session import engine
from app.models.tables import AuditLog


def main():
    # Xóa bảng audit_log cũ nếu đang dùng schema Sprint cũ, rồi tạo lại theo Sprint 7.
    AuditLog.__table__.drop(bind=engine, checkfirst=True)
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    print("OK: recreated audit_log table")


if __name__ == "__main__":
    main()
