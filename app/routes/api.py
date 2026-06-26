from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import warehouse_service as svc
router=APIRouter(prefix='/api')
def username(request):
    u=request.session.get('user')
    if not u: raise ValueError('Not logged in')
    return u['user_name']
def ok(data=None): return {'ok':True,'data':data or {}}
def fail(e): return {'ok':False,'error':str(e)}
@router.post('/gr/confirm')
def gr_confirm(request:Request,po_no:str=Form(...),pallet_id:str=Form(...),barcode:str=Form(...),qty_gr:int=Form(...),db:Session=Depends(get_db)):
    try: return ok(svc.confirm_gr(db,po_no.strip(),pallet_id.strip(),barcode.strip(),qty_gr,username(request)))
    except Exception as e: db.rollback(); return fail(e)
@router.get('/putaway/task/{pallet_id}')
def putaway_task(pallet_id:str,db:Session=Depends(get_db)):
    q=svc.find_putaway_task(db,pallet_id.strip())
    if not q: return {'ok':False,'error':'Không tìm thấy PA chờ Put Away'}
    return ok({'queue_id':q.queue_id,'po_no':q.po_no,'pallet_id':q.pallet_id,'sku':q.sku,'barcode':q.barcode,'qty_gr':q.qty_gr,'qty_putaway':q.qty_putaway,'qty_remain_putaway':q.qty_remain_putaway,'flow_status':q.flow_status})
@router.post('/putaway/confirm')
def putaway_confirm(request:Request,queue_id:int=Form(...),location_id:str=Form(...),qty_putaway:int=Form(...),db:Session=Depends(get_db)):
    try: return ok(svc.confirm_putaway(db,queue_id,location_id.strip(),qty_putaway,username(request)))
    except Exception as e: db.rollback(); return fail(e)
@router.get('/pack/do/{do_no}')
def pack_do(do_no:str,db:Session=Depends(get_db)):
    rows=svc.get_do_lines(db,do_no.strip())
    if not rows: return {'ok':False,'error':'Không tìm thấy DO'}
    return ok({'lines':[{'do_detail_id':r.do_detail_id,'do_no':r.do_no,'store_id':r.store_id,'store_name':r.store_name,'sku':r.sku,'barcode':r.barcode,'qty_do':r.qty_do,'qty_packed':r.qty_packed,'qty_remain':r.qty_remain,'status':r.status} for r in rows]})
@router.post('/pack/confirm')
def pack_confirm(request:Request,do_no:str=Form(...),barcode:str=Form(...),qty_pack:int=Form(...),db:Session=Depends(get_db)):
    try: return ok(svc.confirm_pack(db,do_no.strip(),barcode.strip(),qty_pack,username(request)))
    except Exception as e: db.rollback(); return fail(e)
@router.get('/inventory/search')
def inventory_search(q:str='',db:Session=Depends(get_db)):
    rows=svc.search_inventory(db,q.strip())
    return ok({'rows':[{'sku':r.sku,'barcode':r.barcode,'location_id':r.location_id,'qty_onhand':r.qty_onhand} for r in rows]})
@router.get('/audit/location/{location_id}')
def audit_location(location_id:str,db:Session=Depends(get_db)):
    rows=svc.inventory_by_location(db,location_id.strip())
    return ok({'rows':[{'sku':r.sku,'barcode':r.barcode,'location_id':r.location_id,'qty_onhand':r.qty_onhand} for r in rows]})
@router.post('/audit/confirm')
def audit_confirm(request:Request,location_id:str=Form(...),sku:str=Form(...),physical_qty:int=Form(...),note:str=Form(''),update_inventory:bool=Form(False),db:Session=Depends(get_db)):
    try: return ok(svc.confirm_audit(db,location_id.strip(),sku.strip(),physical_qty,username(request),note,update_inventory))
    except Exception as e: db.rollback(); return fail(e)
