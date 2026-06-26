from app.db.session import SessionLocal
from app.models.tables import AppUser, ProductMaster, LocationMaster, InboundQueue, DoDetail, InventoryBalance
from app.core.security import hash_password
db=SessionLocal()
def add_once(model,key_field,key_value,obj):
    if not db.query(model).filter(getattr(model,key_field)==key_value).first(): db.add(obj)
add_once(AppUser,'user_name','admin',AppUser(user_name='admin',password_hash=hash_password('123456'),role='admin'))
add_once(AppUser,'user_name','worker1',AppUser(user_name='worker1',password_hash=hash_password('123456'),role='worker'))
products=[('SKU001','899000000001','Banh keo A','EA','Bánh kẹo',12),('SKU002','899000000002','Sua hop B','EA','Bơ sữa trứng',24),('SKU003','899000000003','Nuoc rua chen C','EA','Hóa phẩm',12),('SKU004','899000000004','Giay D','EA','Giấy và bông',6),('SKU005','899000000005','Mi goi E','EA','Thực phẩm khô',30)]
for sku,bc,n,u,c,pcb in products: add_once(ProductMaster,'sku',sku,ProductMaster(sku=sku,barcode=bc,product_name=n,uom=u,category=c,pcb=pcb))
for loc in ['A01-001','A01-002','A02-001','A02-002','PACK-STAGE']: add_once(LocationMaster,'location_id',loc,LocationMaster(location_id=loc,zone=loc[:3],location_type='PICK_FACE',status='ACTIVE'))
if not db.query(InboundQueue).filter(InboundQueue.pallet_id=='PA-SAMPLE-001').first(): db.add(InboundQueue(po_no='PO001',pallet_id='PA-SAMPLE-001',barcode='899000000001',sku='SKU001',qty_gr=20,qty_putaway=0,qty_remain_putaway=20,flow_status='WAIT_PUTAWAY'))
if not db.query(InboundQueue).filter(InboundQueue.pallet_id=='PA-SAMPLE-002').first(): db.add(InboundQueue(po_no='PO002',pallet_id='PA-SAMPLE-002',barcode='899000000002',sku='SKU002',qty_gr=30,qty_putaway=10,qty_remain_putaway=20,flow_status='PARTIAL_PUTAWAY'))
if not db.query(InventoryBalance).filter(InventoryBalance.sku=='SKU001',InventoryBalance.location_id=='A01-001').first(): db.add(InventoryBalance(sku='SKU001',barcode='899000000001',location_id='A01-001',qty_onhand=50))
if not db.query(InventoryBalance).filter(InventoryBalance.sku=='SKU002',InventoryBalance.location_id=='A01-002').first(): db.add(InventoryBalance(sku='SKU002',barcode='899000000002',location_id='A01-002',qty_onhand=40))
if not db.query(DoDetail).filter(DoDetail.do_no=='DO001').first():
    db.add(DoDetail(do_no='DO001',store_id='ST001',store_name='Store 001',sku='SKU001',barcode='899000000001',qty_do=10,qty_packed=0,qty_remain=10,status='WAIT'))
    db.add(DoDetail(do_no='DO001',store_id='ST001',store_name='Store 001',sku='SKU002',barcode='899000000002',qty_do=15,qty_packed=0,qty_remain=15,status='WAIT'))
if not db.query(DoDetail).filter(DoDetail.do_no=='DO002').first(): db.add(DoDetail(do_no='DO002',store_id='ST002',store_name='Store 002',sku='SKU003',barcode='899000000003',qty_do=5,qty_packed=0,qty_remain=5,status='WAIT'))
db.commit(); db.close(); print('OK: sample data seeded'); print('Login: admin/123456 or worker1/123456')
