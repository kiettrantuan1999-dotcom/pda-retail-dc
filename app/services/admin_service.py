from datetime import datetime
from app.utils.timezone import now_vn
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.tables import AppUser, SystemSetting


DEFAULT_RESET_PASSWORD = "123456"


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def get_user_by_id(db: Session, user_id: int):
    return db.query(AppUser).filter(AppUser.user_id == user_id).first()


def get_user_by_name(db: Session, user_name: str):
    return db.query(AppUser).filter(AppUser.user_name == clean_text(user_name)).first()


def list_users(db: Session, q: str = "", role: str = "", status: str = ""):
    query = db.query(AppUser)

    q = clean_text(q)
    role = clean_text(role)
    status = clean_text(status)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (AppUser.user_name.ilike(like))
            | (AppUser.full_name.ilike(like))
            | (AppUser.email.ilike(like))
            | (AppUser.phone.ilike(like))
        )

    if role:
        query = query.filter(AppUser.role == role)

    if status == "ACTIVE":
        query = query.filter(AppUser.is_active == True)
    elif status == "INACTIVE":
        query = query.filter(AppUser.is_active == False)

    return query.order_by(AppUser.user_id.asc()).all()


def create_user(
    db: Session,
    *,
    user_name: str,
    password: str,
    full_name: str,
    role: str,
    is_active: bool,
    email: str = "",
    phone: str = "",
    created_by: str = "",
):
    user_name = clean_text(user_name)
    password = password or DEFAULT_RESET_PASSWORD

    if not user_name:
        raise ValueError("Tên đăng nhập không được để trống")

    if get_user_by_name(db, user_name):
        raise ValueError("Tên đăng nhập đã tồn tại")

    user = AppUser(
        user_name=user_name,
        password_hash=hash_password(password),
        full_name=clean_text(full_name),
        role=clean_text(role) or "worker",
        is_active=is_active,
        email=clean_text(email),
        phone=clean_text(phone),
        created_by=clean_text(created_by),
        created_at=now_vn(),
        updated_at=now_vn(),
    )
    db.add(user)
    return user


def update_user(
    db: Session,
    user: AppUser,
    *,
    full_name: str,
    role: str,
    is_active: bool,
    email: str = "",
    phone: str = "",
):
    user.full_name = clean_text(full_name)
    user.role = clean_text(role) or "worker"
    user.is_active = is_active
    user.email = clean_text(email)
    user.phone = clean_text(phone)
    user.updated_at = now_vn()
    db.add(user)
    return user


def reset_password(db: Session, user: AppUser, new_password: str = DEFAULT_RESET_PASSWORD):
    user.password_hash = hash_password(new_password)
    user.updated_at = now_vn()
    db.add(user)
    return user


# =========================
# SYSTEM SETTINGS
# =========================

DEFAULT_SYSTEM_SETTINGS = [
    {
        "setting_key": "warehouse_name",
        "setting_name": "Tên kho",
        "setting_value": "Supra DC Retail",
        "setting_group": "Thông tin kho",
        "value_type": "text",
        "description": "Tên hiển thị của kho trên hệ thống",
    },
    {
        "setting_key": "warehouse_code",
        "setting_name": "Mã kho",
        "setting_value": "DC",
        "setting_group": "Thông tin kho",
        "value_type": "text",
        "description": "Mã kho dùng cho báo cáo và cấu hình nội bộ",
    },
    {
        "setting_key": "pallet_prefix",
        "setting_name": "Prefix mã PA/Pallet",
        "setting_value": "PADCDN",
        "setting_group": "Vận hành",
        "value_type": "text",
        "description": "Tiền tố mặc định khi tạo mã PA/Pallet",
    },
    {
        "setting_key": "default_reset_password",
        "setting_name": "Mật khẩu reset mặc định",
        "setting_value": DEFAULT_RESET_PASSWORD,
        "setting_group": "Tài khoản",
        "value_type": "text",
        "description": "Mật khẩu mặc định khi Admin reset tài khoản",
    },
    {
        "setting_key": "audit_default_limit",
        "setting_name": "Số dòng Audit mặc định",
        "setting_value": "300",
        "setting_group": "Audit",
        "value_type": "number",
        "description": "Số dòng tối đa hiển thị mặc định trên màn hình truy vết",
    },
    {
        "setting_key": "audit_export_enabled",
        "setting_name": "Cho phép xuất Audit",
        "setting_value": "YES",
        "setting_group": "Audit",
        "value_type": "select_yes_no",
        "description": "Bật/tắt chức năng xuất dữ liệu Audit",
    },
    {
        "setting_key": "system_note",
        "setting_name": "Ghi chú hệ thống",
        "setting_value": "",
        "setting_group": "Khác",
        "value_type": "textarea",
        "description": "Ghi chú nội bộ cho Admin",
    },
]


def ensure_default_settings(db: Session):
    for item in DEFAULT_SYSTEM_SETTINGS:
        existing = db.query(SystemSetting).filter(SystemSetting.setting_key == item["setting_key"]).first()
        if existing:
            continue
        db.add(SystemSetting(**item))


def list_settings(db: Session):
    ensure_default_settings(db)
    return (
        db.query(SystemSetting)
        .order_by(SystemSetting.setting_group.asc(), SystemSetting.setting_id.asc())
        .all()
    )


def update_settings(db: Session, form_data: dict, updated_by: str = ""):
    rows = db.query(SystemSetting).filter(SystemSetting.is_editable == True).all()
    now = now_vn()

    for row in rows:
        form_key = f"setting_{row.setting_key}"
        if form_key not in form_data:
            continue
        row.setting_value = clean_text(form_data.get(form_key))
        row.updated_by = clean_text(updated_by)
        row.updated_at = now
        db.add(row)

    return rows
