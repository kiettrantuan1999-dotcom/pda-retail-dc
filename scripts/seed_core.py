from app.db.session import SessionLocal
from app.models.tables import AppRole, AppPermission, RolePermission, AppUser, ProductMaster, LocationMaster
from app.core.security import hash_password

db = SessionLocal()

roles = [
    ("worker", "Công nhân", "Thao tác PDA"),
    ("supervisor", "Giám sát", "Dashboard, báo cáo, nhật ký, kiểm đếm"),
    ("admin", "Quản trị", "Toàn quyền hệ thống"),
]

permissions = [
    ("VIEW_HOME", "Xem trang chủ", "CORE"),
    ("GR_USE", "Sử dụng Nhận hàng", "NHAN_HANG"),
    ("PUTAWAY_USE", "Sử dụng Cất hàng", "CAT_HANG"),
    ("PACK_USE", "Sử dụng Đóng hàng", "DONG_HANG"),
    ("INVENTORY_VIEW", "Xem tồn kho", "TON_KHO"),
    ("AUDIT_USE", "Sử dụng Kiểm đếm", "KIEM_DEM"),
    ("DASHBOARD_VIEW", "Xem dashboard quản lý", "QUAN_LY"),
    ("PRODUCTIVITY_VIEW", "Xem báo cáo năng suất", "BAO_CAO"),
    ("OPERATION_LOG_VIEW", "Xem nhật ký thao tác", "NHAT_KY"),
    ("ERROR_LOG_VIEW", "Xem nhật ký lỗi", "NHAT_KY"),
    ("USER_MANAGE", "Quản lý user", "QUAN_TRI"),
    ("IMPORT_EXPORT", "Import / Export Excel", "QUAN_TRI"),
]

role_permission_map = {
    "worker": ["VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW"],
    "supervisor": [
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW",
        "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW",
        "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW"
    ],
    "admin": [p[0] for p in permissions],
}

for role_code, role_name, desc in roles:
    if not db.query(AppRole).filter(AppRole.role_code == role_code).first():
        db.add(AppRole(role_code=role_code, role_name=role_name, description=desc))

for code, name, module in permissions:
    if not db.query(AppPermission).filter(AppPermission.permission_code == code).first():
        db.add(AppPermission(permission_code=code, permission_name=name, module_name=module))

db.flush()

for role_code, perms in role_permission_map.items():
    for perm in perms:
        exists = db.query(RolePermission).filter(
            RolePermission.role_code == role_code,
            RolePermission.permission_code == perm,
        ).first()
        if not exists:
            db.add(RolePermission(role_code=role_code, permission_code=perm))

default_users = [
    ("admin", "admin"),
    ("worker1", "worker"),
    ("supervisor1", "supervisor"),
]

for user_name, role in default_users:
    user = db.query(AppUser).filter(AppUser.user_name == user_name).first()
    if user:
        user.password_hash = hash_password("123456")
        user.role = role
        user.is_active = True
    else:
        db.add(AppUser(
            user_name=user_name,
            password_hash=hash_password("123456"),
            role=role,
            is_active=True,
        ))

products = [
    ("SKU001", "899000000001", "Bánh kẹo A", "EA", "Bánh kẹo", 12),
    ("SKU002", "899000000002", "Sữa hộp B", "EA", "Bơ sữa trứng", 24),
    ("SKU003", "899000000003", "Nước rửa chén C", "EA", "Hóa phẩm", 12),
]
for sku, barcode, name, uom, cat, pcb in products:
    if not db.query(ProductMaster).filter(ProductMaster.sku == sku).first():
        db.add(ProductMaster(sku=sku, barcode=barcode, product_name=name, uom=uom, category=cat, pcb=pcb))

for loc in ["A01-001", "A01-002", "A02-001", "PACK-STAGE"]:
    if not db.query(LocationMaster).filter(LocationMaster.location_id == loc).first():
        db.add(LocationMaster(location_id=loc, zone=loc[:3], location_type="PICK_FACE", status="ACTIVE"))

db.commit()
db.close()

print("OK: core data seeded")
print("admin / 123456")
print("worker1 / 123456")
print("supervisor1 / 123456")
