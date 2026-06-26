ROLE_LABELS = {
    "worker": "Công nhân",
    "supervisor": "Giám sát",
    "admin": "Quản trị",
}

ROLE_PERMISSIONS = {
    "worker": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW",
    },
    "supervisor": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW",
        "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW",
        "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW",
    },
    "admin": {
        "VIEW_HOME", "GR_USE", "PUTAWAY_USE", "PACK_USE", "INVENTORY_VIEW",
        "AUDIT_USE", "DASHBOARD_VIEW", "PRODUCTIVITY_VIEW",
        "OPERATION_LOG_VIEW", "ERROR_LOG_VIEW",
        "USER_MANAGE", "IMPORT_EXPORT",
    },
}

def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role or "worker", set())
