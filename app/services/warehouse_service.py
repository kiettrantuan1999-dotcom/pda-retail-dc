from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.tables import *
def product_by_barcode(db,barcode): return db.query(ProductMaster).filter(ProductMaster.barcode==barcode).first()
def confirm_gr(db,po_no,pallet_id,barcode,qty_gr,user_name):
    if qty_gr<=0: raise ValueError('qty_gr phải > 0')
    p=product_by_barcode(db,barcode)
    if not p: raise ValueError('Không tìm thấy barcode trong product_master')
    log=GrLog(po_no=po_no,pallet_id=pallet_id,barcode=barcode,sku=p.sku,qty_gr=qty_gr,user_name=user_name)
    q=InboundQueue(po_no=po_no,pallet_id=pallet_id,barcode=barcode,sku=p.sku,qty_gr=qty_gr,qty_putaway=0,qty_remain_putaway=qty_gr,flow_status='WAIT_PUTAWAY',last_update=datetime.utcnow())
    db.add_all([log,q]); db.commit(); return {'queue_id':q.queue_id,'sku':p.sku,'qty_gr':qty_gr}
def find_putaway_task(db,pallet_id):
    return db.query(InboundQueue).filter(InboundQueue.pallet_id==pallet_id, InboundQueue.flow_status.in_(['WAIT_PUTAWAY','PARTIAL_PUTAWAY'])).order_by(InboundQueue.queue_id.asc()).first()
def confirm_putaway(db,queue_id,location_id,qty_putaway,user_name):
    if qty_putaway<=0: raise ValueError('qty_putaway phải > 0')
    q=db.query(InboundQueue).filter(InboundQueue.queue_id==queue_id).with_for_update().first()
    if not q: raise ValueError('Không tìm thấy inbound_queue')
    if q.flow_status=='DONE': raise ValueError('Task đã DONE')
    if qty_putaway>q.qty_remain_putaway: raise ValueError('Qty putaway > qty còn lại')
    loc=db.query(LocationMaster).filter(LocationMaster.location_id==location_id,LocationMaster.status=='ACTIVE').first()
    if not loc: raise ValueError('Location không tồn tại hoặc inactive')
    inv=db.query(InventoryBalance).filter(InventoryBalance.sku==q.sku,InventoryBalance.location_id==location_id).with_for_update().first()
    if not inv:
        inv=InventoryBalance(sku=q.sku,barcode=q.barcode,location_id=location_id,qty_onhand=0); db.add(inv); db.flush()
    inv.qty_onhand+=qty_putaway; inv.last_update=datetime.utcnow()
    q.qty_putaway+=qty_putaway; q.qty_remain_putaway=q.qty_gr-q.qty_putaway; q.flow_status='DONE' if q.qty_remain_putaway==0 else 'PARTIAL_PUTAWAY'; q.last_update=datetime.utcnow()
    db.add(PutawayLog(queue_id=q.queue_id,pallet_id=q.pallet_id,sku=q.sku,barcode=q.barcode,location_id=location_id,qty_putaway=qty_putaway,user_name=user_name))
    db.commit(); return {'status':q.flow_status,'qty_remain_putaway':q.qty_remain_putaway}
def get_do_lines(db,do_no): return db.query(DoDetail).filter(DoDetail.do_no==do_no).order_by(DoDetail.do_detail_id.asc()).all()
def total_sku_stock(db,sku): return db.query(func.coalesce(func.sum(InventoryBalance.qty_onhand),0)).filter(InventoryBalance.sku==sku).scalar() or 0
def confirm_pack(db,do_no,barcode,qty_pack,user_name):
    if qty_pack<=0: raise ValueError('qty_pack phải > 0')
    line=db.query(DoDetail).filter(DoDetail.do_no==do_no,DoDetail.barcode==barcode,DoDetail.status.in_(['WAIT','PARTIAL'])).with_for_update().first()
    if not line: raise ValueError('Không tìm thấy DO line hoặc line đã DONE')
    if qty_pack>line.qty_remain: raise ValueError('qty_pack > qty_remain')
    stock=total_sku_stock(db,line.sku)
    if stock<qty_pack: raise ValueError(f'Tồn không đủ. Tồn hiện tại: {stock}')
    need=qty_pack
    for inv in db.query(InventoryBalance).filter(InventoryBalance.sku==line.sku,InventoryBalance.qty_onhand>0).order_by(InventoryBalance.inventory_id.asc()).with_for_update().all():
        take=min(inv.qty_onhand,need); inv.qty_onhand-=take; inv.last_update=datetime.utcnow(); need-=take
        if need<=0: break
    if need>0: raise ValueError('Không đủ tồn sau khi lock inventory')
    line.qty_packed+=qty_pack; line.qty_remain=line.qty_do-line.qty_packed; line.status='DONE' if line.qty_remain==0 else 'PARTIAL'
    db.add(PackLog(do_no=do_no,store_id=line.store_id,sku=line.sku,barcode=line.barcode,qty_pack=qty_pack,user_name=user_name)); db.commit()
    return {'sku':line.sku,'status':line.status,'qty_remain':line.qty_remain}
def search_inventory(db,q):
    qry=db.query(InventoryBalance)
    if q:
        like=f'%{q}%'; qry=qry.filter((InventoryBalance.sku.ilike(like))|(InventoryBalance.barcode.ilike(like))|(InventoryBalance.location_id.ilike(like)))
    return qry.order_by(InventoryBalance.location_id.asc(),InventoryBalance.sku.asc()).limit(200).all()
def inventory_by_location(db,location_id): return db.query(InventoryBalance).filter(InventoryBalance.location_id==location_id).order_by(InventoryBalance.sku.asc()).all()
def confirm_audit(db,location_id,sku,physical_qty,user_name,note,update_inventory):
    inv=db.query(InventoryBalance).filter(InventoryBalance.location_id==location_id,InventoryBalance.sku==sku).with_for_update().first()
    if not inv: raise ValueError('Không tìm thấy tồn SKU ở location này')
    system_qty=inv.qty_onhand; diff=physical_qty-system_qty
    db.add(AuditLog(sku=inv.sku,barcode=inv.barcode,location_id=location_id,system_qty=system_qty,physical_qty=physical_qty,diff_qty=diff,user_name=user_name,note=note or ''))
    if update_inventory:
        if physical_qty<0: raise ValueError('physical_qty không được âm')
        inv.qty_onhand=physical_qty; inv.last_update=datetime.utcnow()
    db.commit(); return {'system_qty':system_qty,'physical_qty':physical_qty,'diff_qty':diff}
