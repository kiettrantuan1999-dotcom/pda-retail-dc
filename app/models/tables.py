from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
class AppUser(Base):
    __tablename__='app_user'
    user_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_name:Mapped[str]=mapped_column(String(100),unique=True,nullable=False,index=True)
    password_hash:Mapped[str]=mapped_column(String(255),nullable=False)
    role:Mapped[str]=mapped_column(String(50),default='worker')
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class ProductMaster(Base):
    __tablename__='product_master'
    sku:Mapped[str]=mapped_column(String(100),primary_key=True)
    barcode:Mapped[str]=mapped_column(String(100),unique=True,nullable=False,index=True)
    product_name:Mapped[str]=mapped_column(String(255),nullable=False)
    uom:Mapped[str]=mapped_column(String(50),default='EA')
    category:Mapped[str]=mapped_column(String(100),default='')
    pcb:Mapped[int]=mapped_column(Integer,default=1)
class LocationMaster(Base):
    __tablename__='location_master'
    location_id:Mapped[str]=mapped_column(String(100),primary_key=True)
    zone:Mapped[str]=mapped_column(String(100),default='')
    location_type:Mapped[str]=mapped_column(String(100),default='PICK_FACE')
    status:Mapped[str]=mapped_column(String(50),default='ACTIVE')
class InboundQueue(Base):
    __tablename__='inbound_queue'
    queue_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    po_no:Mapped[str]=mapped_column(String(100),index=True)
    pallet_id:Mapped[str]=mapped_column(String(100),index=True)
    barcode:Mapped[str]=mapped_column(String(100),index=True)
    sku:Mapped[str]=mapped_column(String(100),index=True)
    qty_gr:Mapped[int]=mapped_column(Integer)
    qty_putaway:Mapped[int]=mapped_column(Integer,default=0)
    qty_remain_putaway:Mapped[int]=mapped_column(Integer)
    flow_status:Mapped[str]=mapped_column(String(50),default='WAIT_PUTAWAY')
    last_update:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class GrLog(Base):
    __tablename__='gr_log'
    gr_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    po_no:Mapped[str]=mapped_column(String(100)); pallet_id:Mapped[str]=mapped_column(String(100)); barcode:Mapped[str]=mapped_column(String(100)); sku:Mapped[str]=mapped_column(String(100))
    qty_gr:Mapped[int]=mapped_column(Integer); gr_time:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); user_name:Mapped[str]=mapped_column(String(100))
class PutawayLog(Base):
    __tablename__='putaway_log'
    putaway_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    queue_id:Mapped[int]=mapped_column(Integer); pallet_id:Mapped[str]=mapped_column(String(100)); sku:Mapped[str]=mapped_column(String(100)); barcode:Mapped[str]=mapped_column(String(100)); location_id:Mapped[str]=mapped_column(String(100))
    qty_putaway:Mapped[int]=mapped_column(Integer); putaway_time:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); user_name:Mapped[str]=mapped_column(String(100))
class InventoryBalance(Base):
    __tablename__='inventory_balance'
    inventory_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    sku:Mapped[str]=mapped_column(String(100),index=True); barcode:Mapped[str]=mapped_column(String(100),index=True); location_id:Mapped[str]=mapped_column(String(100),index=True)
    qty_onhand:Mapped[int]=mapped_column(Integer,default=0); last_update:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    __table_args__=(UniqueConstraint('sku','location_id',name='uq_inventory_sku_location'),)
class DoDetail(Base):
    __tablename__='do_detail'
    do_detail_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    do_no:Mapped[str]=mapped_column(String(100),index=True); store_id:Mapped[str]=mapped_column(String(100)); store_name:Mapped[str]=mapped_column(String(255)); sku:Mapped[str]=mapped_column(String(100),index=True); barcode:Mapped[str]=mapped_column(String(100),index=True)
    qty_do:Mapped[int]=mapped_column(Integer); qty_packed:Mapped[int]=mapped_column(Integer,default=0); qty_remain:Mapped[int]=mapped_column(Integer); status:Mapped[str]=mapped_column(String(50),default='WAIT')
class PackLog(Base):
    __tablename__='pack_log'
    pack_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    do_no:Mapped[str]=mapped_column(String(100)); store_id:Mapped[str]=mapped_column(String(100)); sku:Mapped[str]=mapped_column(String(100)); barcode:Mapped[str]=mapped_column(String(100)); qty_pack:Mapped[int]=mapped_column(Integer); pack_time:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); user_name:Mapped[str]=mapped_column(String(100))
class AuditLog(Base):
    __tablename__='audit_log'
    audit_id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    sku:Mapped[str]=mapped_column(String(100)); barcode:Mapped[str]=mapped_column(String(100)); location_id:Mapped[str]=mapped_column(String(100)); system_qty:Mapped[int]=mapped_column(Integer); physical_qty:Mapped[int]=mapped_column(Integer); diff_qty:Mapped[int]=mapped_column(Integer)
    audit_time:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); user_name:Mapped[str]=mapped_column(String(100)); note:Mapped[str]=mapped_column(Text,default='')
