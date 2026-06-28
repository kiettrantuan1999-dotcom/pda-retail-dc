from app.db.session import SessionLocal

from app.models.tables import (
    ProductMaster,
    LocationMaster,
    InventoryBalance,
    PalletHeader,
    PalletDetail,
)

db = SessionLocal()

PO_NO = "PO_TEST_INV_001"


def main():
    print("Cleaning old inventory seed data...")

    # Xóa dữ liệu test cũ
    db.query(PalletDetail).delete()
    db.query(PalletHeader).delete()
    db.query(InventoryBalance).delete()
    db.commit()

    # =========================
    # PRODUCT MASTER
    # =========================
    products = [
        ("10100001", "8938505900011", "Mì Omachi Thịt", "Thùng", "Thực phẩm"),
        ("10100002", "8938505900012", "Mì Kokomi", "Thùng", "Thực phẩm"),
        ("10100003", "8938505900013", "Nước mắm Nam Ngư", "Thùng", "Thực phẩm"),
        ("10100004", "8938505900014", "Dầu Neptune", "Thùng", "Thực phẩm"),
        ("10100005", "8938505900015", "Sữa Vinamilk", "Thùng", "Bơ sữa"),
        ("10100006", "8938505900016", "Coca Cola 330ml", "Thùng", "Đồ uống"),
        ("10100007", "8938505900017", "Pepsi 330ml", "Thùng", "Đồ uống"),
        ("10100008", "8938505900018", "Bánh AFC", "Thùng", "Bánh kẹo"),
        ("10100009", "8938505900019", "Nước suối Lavie", "Thùng", "Đồ uống"),
        ("10100010", "8938505900020", "Bột giặt Aba", "Thùng", "Hóa phẩm"),
    ]

    for sku, barcode, name, uom, category in products:
        item = db.query(ProductMaster).filter(ProductMaster.sku == sku).first()

        if item:
            item.barcode = barcode
            item.product_name = name
            item.uom = uom
            item.category = category
        else:
            db.add(
                ProductMaster(
                    sku=sku,
                    barcode=barcode,
                    product_name=name,
                    uom=uom,
                    category=category,
                )
            )

    db.commit()

    # =========================
    # LOCATION MASTER
    # =========================
    locations = [
        ("A01-001", "A01", "PICK_FACE", "ACTIVE", 100, 1),
        ("A01-002", "A01", "PICK_FACE", "ACTIVE", 100, 2),
        ("A01-003", "A01", "PICK_FACE", "ACTIVE", 100, 3),
        ("A02-001", "A02", "PICK_FACE", "ACTIVE", 100, 4),
        ("A02-002", "A02", "PICK_FACE", "ACTIVE", 100, 5),
    ]

    for location_id, zone, location_type, status, max_capacity, pick_index in locations:
        loc = (
            db.query(LocationMaster)
            .filter(LocationMaster.location_id == location_id)
            .first()
        )

        if loc:
            loc.zone = zone
            loc.location_type = location_type
            loc.status = status
            loc.max_capacity = max_capacity
            loc.pick_index = pick_index
        else:
            db.add(
                LocationMaster(
                    location_id=location_id,
                    zone=zone,
                    location_type=location_type,
                    status=status,
                    max_capacity=max_capacity,
                    pick_index=pick_index,
                )
            )

    db.commit()

    # =========================
    # INVENTORY DATA
    # Lưu ý:
    # pallet_detail hiện tại chưa có location_id.
    # Location hiện được quản lý chính qua inventory_balance.
    # =========================
    inventory_rows = [
        ("PA000001", "A01-001", "10100001", "8938505900011", 50),
        ("PA000001", "A01-001", "10100002", "8938505900012", 40),
        ("PA000002", "A01-002", "10100003", "8938505900013", 35),
        ("PA000002", "A01-002", "10100004", "8938505900014", 20),
        ("PA000003", "A01-003", "10100005", "8938505900015", 65),
        ("PA000003", "A01-003", "10100006", "8938505900016", 18),
        ("PA000004", "A02-001", "10100007", "8938505900017", 75),
        ("PA000004", "A02-001", "10100008", "8938505900018", 30),
        ("PA000005", "A02-002", "10100009", "8938505900019", 90),
        ("PA000005", "A02-002", "10100010", "8938505900020", 25),
    ]

    # =========================
    # PALLET HEADER
    # =========================
    created_pallets = set()

    for pallet_id, location_id, sku, barcode, qty in inventory_rows:
        if pallet_id in created_pallets:
            continue

        db.add(
            PalletHeader(
                pallet_id=pallet_id,
                po_no=PO_NO,
                status="PUTAWAY_DONE",
                created_by="SYSTEM",
            )
        )

        created_pallets.add(pallet_id)

    db.commit()

    # =========================
    # PALLET DETAIL + INVENTORY BALANCE
    # =========================
    for pallet_id, location_id, sku, barcode, qty in inventory_rows:
        db.add(
            PalletDetail(
                pallet_id=pallet_id,
                po_no=PO_NO,
                sku=sku,
                barcode=barcode,
                qty_gr=qty,
                qty_putaway=qty,
                qty_remain_putaway=0,
                status="DONE",
            )
        )

        db.add(
            InventoryBalance(
                sku=sku,
                barcode=barcode,
                location_id=location_id,
                qty_onhand=qty,
            )
        )

    db.commit()

    print("=" * 50)
    print("Inventory seed success")
    print(f"PO        : {PO_NO}")
    print(f"Products  : {len(products)}")
    print(f"Locations : {len(locations)}")
    print(f"Pallets   : {len(created_pallets)}")
    print(f"Inventory : {len(inventory_rows)}")
    print("=" * 50)

    print("Barcode test:")
    print("8938505900011")
    print("8938505900012")
    print("8938505900014")


if __name__ == "__main__":
    try:
        main()
    finally:
        db.close()