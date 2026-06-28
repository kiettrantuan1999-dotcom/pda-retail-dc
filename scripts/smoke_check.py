import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text


def main():
    from app.main import app  # noqa: F401
    from app.db.session import SessionLocal, engine
    from app.models.tables import AppUser, ProductMaster, InventoryBalance, AuditLog, SystemSetting
    from app.routes import admin, audit, auth, inventory, pack, pages, putaway, supervisor  # noqa: F401

    inspector = inspect(engine)
    required_tables = [
        "app_user",
        "product_master",
        "location_master",
        "inventory_balance",
        "audit_log",
        "system_setting",
    ]

    missing = [table for table in required_tables if not inspector.has_table(table)]
    if missing:
        raise RuntimeError(f"Thiếu bảng: {', '.join(missing)}. Hãy chạy: python scripts/init_db.py")

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        admin_user = db.query(AppUser).filter(AppUser.user_name == "admin").first()
        if not admin_user:
            raise RuntimeError("Chưa có user admin. Hãy chạy: python scripts/seed_all.py")

        counts = {
            "users": db.query(AppUser).count(),
            "products": db.query(ProductMaster).count(),
            "inventory": db.query(InventoryBalance).count(),
            "audit": db.query(AuditLog).count(),
            "settings": db.query(SystemSetting).count(),
        }
    finally:
        db.close()

    print("OK: smoke check passed")
    for key, value in counts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
