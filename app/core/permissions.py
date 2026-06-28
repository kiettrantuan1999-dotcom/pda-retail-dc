ROLE_LABELS = {
    "worker": "Công nhân",
    "supervisor": "Giám sát",
    "admin": "Quản trị",
}

PERMISSION_LABELS = {
    "VIEW_HOME": "Xem trang chủ",
    "GR_USE": "Thao tác nhận hàng",
    "PUTAWAY_USE": "Thao tác cất hàng",
    "PACK_USE": "Thao tác đóng hàng",
    "STAGING_USE": "Thao tác tập kết hàng",
    "INVENTORY_VIEW": "Xem / thao tác kiểm tra tồn",
    "AUDIT_USE": "Truy vết thao tác",
    "DASHBOARD_VIEW": "Xem dashboard quản lý",
    "PRODUCTIVITY_VIEW": "Xem năng suất",
    "OPERATION_LOG_VIEW": "Xem nhật ký vận hành",
    "ERROR_LOG_VIEW": "Xem nhật ký lỗi",
    "USER_MANAGE": "Quản trị người dùng",
    "SETTING_MANAGE": "Quản lý cấu hình hệ thống",
    "IMPORT_EXPORT": "Import / Export dữ liệu",
}

PERMISSION_MODULES = {
    "VIEW_HOME": "Nền tảng",
    "GR_USE": "Nhận hàng",
    "PUTAWAY_USE": "Cất hàng",
    "PACK_USE": "Đóng hàng",
    "STAGING_USE": "Tập kết hàng",
    "INVENTORY_VIEW": "Kiểm tra tồn",
    "AUDIT_USE": "Audit",
    "DASHBOARD_VIEW": "Quản lý",
    "PRODUCTIVITY_VIEW": "Quản lý",
    "OPERATION_LOG_VIEW": "Nhật ký",
    "ERROR_LOG_VIEW": "Nhật ký",
    "USER_MANAGE": "Quản trị",
    "SETTING_MANAGE": "Quản trị",
    "IMPORT_EXPORT": "Dữ liệu",
}

ROLE_PERMISSIONS = {
    "worker": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "STAGING_USE", "INVENTORY_VIEW",
    },
    "supervisor": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "STAGING_USE", "INVENTORY_VIEW",
        "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW",
        "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW",
    },
    "admin": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "STAGING_USE", "INVENTORY_VIEW",
        "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW",
        "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW",
        "USER_MANAGE", "SETTING_MANAGE", "IMPORT_EXPORT",
    },
}

ROLE_OPTIONS = ["worker", "supervisor", "admin"]


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role or "worker", set())
