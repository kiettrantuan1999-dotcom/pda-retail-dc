from app.db.session import SessionLocal
from app.models.tables import AppUser
from app.core.security import hash_password

db = SessionLocal()

for name in ["admin", "worker1"]:
    user = db.query(AppUser).filter(AppUser.user_name == name).first()
    if user:
        user.password_hash = hash_password("123456")
        print(f"Reset password for {name}")
    else:
        print(f"User not found: {name}")

db.commit()
db.close()

print("OK: password reset to 123456")