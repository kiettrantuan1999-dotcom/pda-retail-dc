from random import choice, randint
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.tables import AuditLog

db = SessionLocal()

operations = [
    "GR",
    "PUTAWAY",
    "COUNT",
    "ADJUST",
    "PACK"
]

users = [
    "Nguyễn Văn A",
    "Trần Văn B",
    "Lê Minh C",
    "Supervisor"
]

locations = [
    "A01-01-01",
    "A01-01-02",
    "A02-03-01",
    "B01-01-01",
    "C03-02-01"
]

skus = [
    "10303906",
    "10141530",
    "10012211",
    "10455678",
    "10889900"
]

barcodes = [
    "8992775347256",
    "8936134363112",
    "8851234567890",
    "8998888888888",
    "8939999999999"
]

for i in range(30):

    qty_before = randint(10, 100)
    qty_after = max(0, qty_before + randint(-5, 5))

    log = AuditLog(
        event_time=datetime.now() - timedelta(minutes=i * 8),
        operation=choice(operations),
        user_name=choice(users),
        sku=choice(skus),
        barcode=choice(barcodes),
        pallet_id=f"PADCDN260628{1000+i}",
        location_id=choice(locations),
        reference_no=choice([
            "4901301088",
            "4901300277",
            "DO000123",
            "DO000456",
            "COUNT0001"
        ]),
        qty_before=qty_before,
        qty_after=qty_after,
        remark="Seed dữ liệu test"
    )

    db.add(log)

db.commit()
db.close()

print("OK - Seeded 30 audit logs")