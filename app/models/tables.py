from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


# =========================
# CORE / AUTH / ROLE
# =========================

class AppUser(Base):
    __tablename__ = "app_user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="worker", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppRole(Base):
    __tablename__ = "app_role"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppPermission(Base):
    __tablename__ = "app_permission"

    permission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    permission_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    permission_name: Mapped[str] = mapped_column(String(255), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RolePermission(Base):
    __tablename__ = "role_permission"

    role_permission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    permission_code: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("role_code", "permission_code", name="uq_role_permission"),)


# =========================
# MASTER DATA
# =========================

class ProductMaster(Base):
    __tablename__ = "product_master"

    sku: Mapped[str] = mapped_column(String(100), primary_key=True)
    barcode: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    uom: Mapped[str] = mapped_column(String(50), default="EA")
    category: Mapped[str] = mapped_column(String(100), default="")
    pcb: Mapped[int] = mapped_column(Integer, default=1)


class LocationMaster(Base):
    __tablename__ = "location_master"

    location_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    zone: Mapped[str] = mapped_column(String(100), default="")
    location_type: Mapped[str] = mapped_column(String(100), default="PICK_FACE")
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")


# =========================
# INBOUND
# =========================

class PalletHeader(Base):
    __tablename__ = "pallet_header"

    pallet_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    po_no: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="GR_IN_PROGRESS", index=True)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PalletDetail(Base):
    __tablename__ = "pallet_detail"

    pallet_detail_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pallet_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    po_no: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    barcode: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    qty_gr: Mapped[int] = mapped_column(Integer, default=0)
    qty_putaway: Mapped[int] = mapped_column(Integer, default=0)
    qty_remain_putaway: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="WAIT_PUTAWAY", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("pallet_id", "sku", name="uq_pallet_sku"),)


# Giữ bảng cũ để không làm vỡ dữ liệu đang có. Phase 2 sẽ chuyển logic sang pallet_header/detail.
class InboundQueue(Base):
    __tablename__ = "inbound_queue"

    queue_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_no: Mapped[str] = mapped_column(String(100), index=True)
    pallet_id: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    qty_gr: Mapped[int] = mapped_column(Integer)
    qty_putaway: Mapped[int] = mapped_column(Integer, default=0)
    qty_remain_putaway: Mapped[int] = mapped_column(Integer)
    flow_status: Mapped[str] = mapped_column(String(50), default="WAIT_PUTAWAY")
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GrLog(Base):
    __tablename__ = "gr_log"

    gr_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_no: Mapped[str] = mapped_column(String(100), index=True)
    pallet_id: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    qty_gr: Mapped[int] = mapped_column(Integer)
    gr_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_name: Mapped[str] = mapped_column(String(100), index=True)


class PutawayLog(Base):
    __tablename__ = "putaway_log"

    putaway_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    queue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pallet_detail_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pallet_id: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    location_id: Mapped[str] = mapped_column(String(100), index=True)
    qty_putaway: Mapped[int] = mapped_column(Integer)
    putaway_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_name: Mapped[str] = mapped_column(String(100), index=True)


# =========================
# INVENTORY
# =========================

class InventoryBalance(Base):
    __tablename__ = "inventory_balance"

    inventory_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    location_id: Mapped[str] = mapped_column(String(100), index=True)
    qty_onhand: Mapped[int] = mapped_column(Integer, default=0)
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("sku", "location_id", name="uq_inventory_sku_location"),)


# =========================
# OUTBOUND
# =========================

class DoDetail(Base):
    __tablename__ = "do_detail"

    do_detail_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    do_no: Mapped[str] = mapped_column(String(100), index=True)
    store_id: Mapped[str] = mapped_column(String(100))
    store_name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    qty_do: Mapped[int] = mapped_column(Integer)
    qty_packed: Mapped[int] = mapped_column(Integer, default=0)
    qty_remain: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="WAIT")


class PackLog(Base):
    __tablename__ = "pack_log"

    pack_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    do_no: Mapped[str] = mapped_column(String(100), index=True)
    store_id: Mapped[str] = mapped_column(String(100))
    sku: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    qty_pack: Mapped[int] = mapped_column(Integer)
    pack_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_name: Mapped[str] = mapped_column(String(100), index=True)


# =========================
# AUDIT
# =========================

class AuditLog(Base):
    __tablename__ = "audit_log"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), index=True)
    barcode: Mapped[str] = mapped_column(String(100), index=True)
    location_id: Mapped[str] = mapped_column(String(100), index=True)
    system_qty: Mapped[int] = mapped_column(Integer)
    physical_qty: Mapped[int] = mapped_column(Integer)
    diff_qty: Mapped[int] = mapped_column(Integer)
    audit_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_name: Mapped[str] = mapped_column(String(100), index=True)
    note: Mapped[str] = mapped_column(Text, default="")


# =========================
# LOG / TRACEABILITY
# =========================

class OperationLog(Base):
    __tablename__ = "operation_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    module_name: Mapped[str] = mapped_column(String(100), index=True)
    user_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    reference_type: Mapped[str] = mapped_column(String(100), default="", index=True)
    reference_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    request_payload: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(100), default="")
    device_info: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ErrorLog(Base):
    __tablename__ = "error_log"

    error_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    function_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    user_name: Mapped[str] = mapped_column(String(100), default="", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    stack_trace: Mapped[str] = mapped_column(Text, default="")
    request_payload: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(100), default="")
    device_info: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
