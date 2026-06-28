import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.tables import (
    AppPermission,
    AppRole,
    AppUser,
    AuditLog,
    DoDetail,
    InboundQueue,
    InventoryBalance,
    InventoryCountDetail,
    InventoryCountHeader,
    LocationMaster,
    PoDetail,
    PoHeader,
    ProductMaster,
    RolePermission,
    SupplierMaster,
    SystemSetting,
)
from app.services.admin_service import ensure_default_settings


def get_or_create(db, model, defaults=None, **filters):
    obj = db.query(model).filter_by(**filters).first()
    if obj:
        return obj, False
    data = dict(filters)
    if defaults:
        data.update(defaults)
    obj = model(**data)
    db.add(obj)
    return obj, True


def seed_roles_permissions(db):
    roles = [
        ("worker", "Công nhân", "Thao tác PDA"),
        ("supervisor", "Giám sát", "Dashboard, audit, kiểm kê"),
        ("admin", "Quản trị", "Toàn quyền hệ thống"),
    ]

    permissions = [
        ("VIEW_HOME", "Xem trang chủ", "CORE"),
        ("GR_USE", "Sử dụng Nhận hàng", "NHẬN HÀNG"),
        ("PUTAWAY_USE", "Sử dụng Cất hàng", "CẤT HÀNG"),
        ("PACK_USE", "Sử dụng Đóng hàng", "ĐÓNG HÀNG"),
        ("INVENTORY_VIEW", "Xem tồn kho", "TỒN KHO"),
        ("AUDIT_USE", "Sử dụng Audit", "AUDIT"),
        ("DASHBOARD_VIEW", "Xem dashboard", "DASHBOARD"),
        ("PRODUCTIVITY_VIEW", "Xem báo cáo năng suất", "BÁO CÁO"),
        ("OPERATION_LOG_VIEW", "Xem nhật ký thao tác", "NHẬT KÝ"),
        ("ERROR_LOG_VIEW", "Xem nhật ký lỗi", "NHẬT KÝ"),
        ("USER_MANAGE", "Quản lý người dùng", "QUẢN TRỊ"),
        ("IMPORT_EXPORT", "Import / Export Excel", "QUẢN TRỊ"),
        ("ADMIN_SETTINGS", "Cấu hình hệ thống", "QUẢN TRỊ"),
    ]

    for role_code, role_name, desc in roles:
        get_or_create(
            db,
            AppRole,
            role_code=role_code,
            defaults={"role_name": role_name, "description": desc, "is_active": True},
        )

    for code, name, module in permissions:
        get_or_create(
            db,
            AppPermission,
            permission_code=code,
            defaults={"permission_name": name, "module_name": module},
        )

    role_permission_map = {
        "worker": ["VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW"],
        "supervisor": [
            "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW",
            "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW", "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW",
        ],
        "admin": [p[0] for p in permissions],
    }

    for role_code, perms in role_permission_map.items():
        for perm in perms:
            get_or_create(db, RolePermission, role_code=role_code, permission_code=perm)


def seed_users(db):
    users = [
        ("admin", "Quản trị hệ thống", "admin"),
        ("supervisor1", "Giám sát test", "supervisor"),
        ("worker1", "Nhân viên test", "worker"),
    ]

    for user_name, full_name, role in users:
        user = db.query(AppUser).filter(AppUser.user_name == user_name).first()
        if user:
            user.password_hash = hash_password("123456")
            user.full_name = full_name
            user.role = role
            user.is_active = True
            user.updated_at = datetime.utcnow()
        else:
            db.add(AppUser(
                user_name=user_name,
                password_hash=hash_password("123456"),
                full_name=full_name,
                role=role,
                is_active=True,
                created_by="seed_all",
            ))


def seed_master_data(db):
    products = [
        ("SKU001", "899000000001", "Bánh kẹo A", "EA", "Bánh kẹo", 12),
        ("SKU002", "899000000002", "Sữa hộp B", "EA", "Bơ sữa trứng", 24),
        ("SKU003", "899000000003", "Nước rửa chén C", "EA", "Hóa phẩm", 12),
        ("SKU004", "899000000004", "Giấy D", "EA", "Giấy và bông", 6),
        ("SKU005", "899000000005", "Mì gói E", "EA", "Thực phẩm khô", 30),
    ]

    for sku, barcode, name, uom, category, pcb in products:
        get_or_create(
            db,
            ProductMaster,
            sku=sku,
            defaults={
                "barcode": barcode,
                "product_name": name,
                "uom": uom,
                "category": category,
                "pcb": pcb,
            },
        )

    locations = [
        ("A01-001", "A01", "PICK_FACE", 100),
        ("A01-002", "A01", "PICK_FACE", 100),
        ("A02-001", "A02", "PICK_FACE", 100),
        ("A02-002", "A02", "PICK_FACE", 100),
        ("PACK-STAGE", "PACK", "STAGING", 999),
    ]

    for location_id, zone, location_type, max_capacity in locations:
        get_or_create(
            db,
            LocationMaster,
            location_id=location_id,
            defaults={
                "zone": zone,
                "location_type": location_type,
                "status": "ACTIVE",
                "max_capacity": max_capacity,
            },
        )


def seed_inbound(db):
    get_or_create(
        db,
        SupplierMaster,
        supplier_code="NCC001",
        defaults={"supplier_name": "Nhà cung cấp test", "status": "ACTIVE"},
    )

    get_or_create(
        db,
        PoHeader,
        po_no="PO_TEST_001",
        defaults={"supplier_code": "NCC001", "supplier_name": "Nhà cung cấp test", "status": "WAIT_GR"},
    )

    po_lines = [
        ("SKU001", "899000000001", "Bánh kẹo A", 240),
        ("SKU002", "899000000002", "Sữa hộp B", 120),
        ("SKU003", "899000000003", "Nước rửa chén C", 60),
    ]
    for sku, barcode, name, qty in po_lines:
        get_or_create(
            db,
            PoDetail,
            po_no="PO_TEST_001",
            sku=sku,
            defaults={
                "barcode": barcode,
                "product_name": name,
                "qty_order": qty,
                "qty_received": 0,
                "qty_remaining": qty,
                "status": "WAIT_GR",
            },
        )

    queue_rows = [
        ("PO_TEST_001", "PA-SAMPLE-001", "899000000001", "SKU001", 20, 0, 20, "WAIT_PUTAWAY"),
        ("PO_TEST_001", "PA-SAMPLE-002", "899000000002", "SKU002", 30, 10, 20, "PARTIAL_PUTAWAY"),
    ]

    for po_no, pallet_id, barcode, sku, qty_gr, qty_putaway, qty_remain, status in queue_rows:
        if not db.query(InboundQueue).filter(InboundQueue.pallet_id == pallet_id, InboundQueue.sku == sku).first():
            db.add(InboundQueue(
                po_no=po_no,
                pallet_id=pallet_id,
                barcode=barcode,
                sku=sku,
                qty_gr=qty_gr,
                qty_putaway=qty_putaway,
                qty_remain_putaway=qty_remain,
                flow_status=status,
            ))


def seed_inventory(db):
    rows = [
        ("SKU001", "899000000001", "A01-001", 50),
        ("SKU002", "899000000002", "A01-002", 40),
        ("SKU003", "899000000003", "A02-001", 30),
    ]
    for sku, barcode, location_id, qty in rows:
        get_or_create(
            db,
            InventoryBalance,
            sku=sku,
            location_id=location_id,
            defaults={"barcode": barcode, "qty_onhand": qty},
        )

    get_or_create(
        db,
        InventoryCountHeader,
        count_no="COUNT_TEST_001",
        defaults={
            "count_name": "Phiếu kiểm kê test",
            "status": "OPEN",
            "total_locations": 2,
            "total_lines": 2,
            "created_by": "admin",
        },
    )

    count_lines = [
        ("A01-001", "SKU001", "899000000001", "Bánh kẹo A", 50),
        ("A01-002", "SKU002", "899000000002", "Sữa hộp B", 40),
    ]
    for location_id, sku, barcode, name, expected in count_lines:
        get_or_create(
            db,
            InventoryCountDetail,
            count_no="COUNT_TEST_001",
            location_id=location_id,
            sku=sku,
            defaults={
                "barcode": barcode,
                "product_name": name,
                "expected_qty": expected,
                "status": "WAIT_COUNT",
            },
        )


def seed_outbound(db):
    do_rows = [
        ("DO001", "ST001", "Cửa hàng test 001", "SKU001", "899000000001", "Bánh kẹo A", 10),
        ("DO001", "ST001", "Cửa hàng test 001", "SKU002", "899000000002", "Sữa hộp B", 15),
        ("DO002", "ST002", "Cửa hàng test 002", "SKU003", "899000000003", "Nước rửa chén C", 5),
    ]

    for do_no, store_id, store_name, sku, barcode, product_name, qty in do_rows:
        exists = db.query(DoDetail).filter(DoDetail.do_no == do_no, DoDetail.store_id == store_id, DoDetail.sku == sku).first()
        if not exists:
            db.add(DoDetail(
                do_no=do_no,
                store_id=store_id,
                store_name=store_name,
                sku=sku,
                barcode=barcode,
                product_name=product_name,
                uom="EA",
                qty_do=qty,
                qty_packed=0,
                qty_remain=qty,
                status="WAIT_PICK",
            ))


def seed_audit(db):
    rows = [
        ("GR", "PO_TEST_001", "PA-SAMPLE-001", "", "SKU001", "899000000001", 0, 20, "worker1", "Nhận hàng test"),
        ("PUTAWAY", "PO_TEST_001", "PA-SAMPLE-001", "A01-001", "SKU001", "899000000001", 20, 0, "worker1", "Cất hàng test"),
        ("COUNT", "COUNT_TEST_001", "", "A01-001", "SKU001", "899000000001", 50, 50, "supervisor1", "Kiểm kê test"),
        ("ADJUST", "COUNT_TEST_001", "", "A01-002", "SKU002", "899000000002", 40, 39, "supervisor1", "Điều chỉnh test"),
        ("PACK", "DO001", "", "PACK-STAGE", "SKU001", "899000000001", 10, 0, "worker1", "Đóng hàng test"),
    ]

    base_time = datetime.utcnow() - timedelta(hours=2)
    for idx, (operation, ref, pallet, location, sku, barcode, before, after, user, remark) in enumerate(rows):
        exists = db.query(AuditLog).filter(
            AuditLog.operation == operation,
            AuditLog.reference_no == ref,
            AuditLog.sku == sku,
            AuditLog.remark == remark,
        ).first()
        if not exists:
            db.add(AuditLog(
                event_time=base_time + timedelta(minutes=idx * 15),
                operation=operation,
                reference_no=ref,
                pallet_id=pallet,
                location_id=location,
                sku=sku,
                barcode=barcode,
                qty_before=before,
                qty_after=after,
                qty_change=after - before,
                user_name=user,
                remark=remark,
            ))


def main():
    db = SessionLocal()
    try:
        seed_roles_permissions(db)
        seed_users(db)
        seed_master_data(db)
        seed_inbound(db)
        seed_inventory(db)
        seed_outbound(db)
        ensure_default_settings(db)
        seed_audit(db)
        db.commit()
        print("OK: v1.0 seed data completed")
        print("Login: admin / 123456")
        print("Login: supervisor1 / 123456")
        print("Login: worker1 / 123456")
        print("PO test: PO_TEST_001")
        print("DO test: DO001, DO002")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
