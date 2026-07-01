from datetime import datetime
from app.utils.timezone import now_vn
from app.db import supabase


def confirm_gr(po_no: str, pallet_id: str, barcode: str, qty: int):
    now = now_vn().isoformat()

    # Step 1: Check PO
    po_header = (
        supabase.table("po_header")
        .select("*")
        .eq("po_no", po_no)
        .execute()
    )

    if not po_header.data:
        raise Exception("PO not found")

    # Step 2: Check barcode in PO
    po_detail = (
        supabase.table("po_detail")
        .select("*")
        .eq("po_no", po_no)
        .eq("barcode", barcode)
        .execute()
    )

    if not po_detail.data:
        raise Exception("Barcode not in PO")

    po_line = po_detail.data[0]

    sku = po_line["sku"]
    qty_order = int(po_line["qty_order"])
    qty_received = int(po_line.get("qty_received") or 0)

    # Step 3: Check duplicate pallet
    existing_pallet = (
        supabase.table("pallet_header")
        .select("pallet_id")
        .eq("pallet_id", pallet_id)
        .execute()
    )

    if existing_pallet.data:
        raise Exception("Duplicate pallet")

    # Step 4: Check qty
    qty = int(qty)

    if qty <= 0:
        raise Exception("Qty must be greater than 0")

    if qty_received + qty > qty_order:
        raise Exception(
            f"Over receipt: ordered={qty_order}, received={qty_received}, input={qty}"
        )

    # Step 5: Update PO detail
    new_qty_received = qty_received + qty

    line_status = "DONE" if new_qty_received >= qty_order else "PARTIAL"

    supabase.table("po_detail").update({
        "qty_received": new_qty_received,
        "status": line_status
    }).eq("po_no", po_no).eq("barcode", barcode).execute()

    # Step 6: Create pallet header
    supabase.table("pallet_header").insert({
        "pallet_id": pallet_id,
        "po_no": po_no,
        "status": "OPEN",
        "created_at": now
    }).execute()

    # Step 7: Create pallet detail
    supabase.table("pallet_detail").insert({
        "pallet_id": pallet_id,
        "po_no": po_no,
        "sku": sku,
        "barcode": barcode,
        "qty": qty,
        "status": "RECEIVED",
        "created_at": now
    }).execute()

    # Step 8: Create inbound queue
    supabase.table("inbound_queue").insert({
        "po_no": po_no,
        "pallet_id": pallet_id,
        "sku": sku,
        "barcode": barcode,
        "qty_gr": qty,
        "qty_putaway": 0,
        "qty_remain_putaway": qty,
        "flow_status": "WAIT_PUTAWAY",
        "last_update": now
    }).execute()

    # Step 9: Write GR log
    supabase.table("gr_log").insert({
        "po_no": po_no,
        "pallet_id": pallet_id,
        "sku": sku,
        "barcode": barcode,
        "qty": qty,
        "action": "CONFIRM_GR",
        "created_at": now
    }).execute()

    # Step 10: Return
    return {
        "status": "success",
        "po_no": po_no,
        "pallet_id": pallet_id,
        "sku": sku,
        "barcode": barcode,
        "qty": qty
    }