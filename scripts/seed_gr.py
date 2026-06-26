from app.db.session import SessionLocal
from app.models.tables import SupplierMaster, ProductMaster, PoHeader, PoDetail

db = SessionLocal()

supplier = db.query(SupplierMaster).filter(
    SupplierMaster.supplier_code == "NCC001"
).first()

if not supplier:
    db.add(SupplierMaster(
        supplier_code="NCC001",
        supplier_name="Nhà cung cấp test",
        status="ACTIVE",
    ))

products = [
    ("SKU001", "899000000001", "Bánh kẹo A", "EA", "Bánh kẹo", 12),
    ("SKU002", "899000000002", "Sữa hộp B", "EA", "Bơ sữa trứng", 24),
    ("SKU003", "899000000003", "Nước rửa chén C", "EA", "Hóa phẩm", 12),
]

for sku, barcode, name, uom, category, pcb in products:
    p = db.query(ProductMaster).filter(ProductMaster.sku == sku).first()
    if not p:
        db.add(ProductMaster(
            sku=sku,
            barcode=barcode,
            product_name=name,
            uom=uom,
            category=category,
            pcb=pcb,
        ))

po = db.query(PoHeader).filter(PoHeader.po_no == "PO_TEST_001").first()
if not po:
    db.add(PoHeader(
        po_no="PO_TEST_001",
        supplier_code="NCC001",
        supplier_name="Nhà cung cấp test",
        status="WAIT_GR",
    ))

po_lines = [
    ("PO_TEST_001", "SKU001", "899000000001", "Bánh kẹo A", 240),
    ("PO_TEST_001", "SKU002", "899000000002", "Sữa hộp B", 120),
    ("PO_TEST_001", "SKU003", "899000000003", "Nước rửa chén C", 60),
]

for po_no, sku, barcode, product_name, qty_order in po_lines:
    line = db.query(PoDetail).filter(
        PoDetail.po_no == po_no,
        PoDetail.sku == sku,
    ).first()

    if not line:
        db.add(PoDetail(
            po_no=po_no,
            sku=sku,
            barcode=barcode,
            product_name=product_name,
            qty_order=qty_order,
            qty_received=0,
            qty_remaining=qty_order,
            status="WAIT_GR",
        ))

db.commit()
db.close()

print("OK: seeded GR sample data")
print("PO test: PO_TEST_001")