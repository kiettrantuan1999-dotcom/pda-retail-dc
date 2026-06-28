import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import Base, SessionLocal, engine
from app.models.tables import SystemSetting
from app.services.admin_service import ensure_default_settings


def main():
    Base.metadata.create_all(bind=engine, tables=[SystemSetting.__table__])

    db = SessionLocal()
    try:
        ensure_default_settings(db)
        db.commit()
        print("OK: Sprint 10.3 system settings migration completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
