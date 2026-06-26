from sqlalchemy.orm import Session
from app.models.tables import AppUser
from app.core.security import verify_password

def authenticate_user(db: Session, user_name: str, password: str):
    user = db.query(AppUser).filter(
        AppUser.user_name == user_name,
        AppUser.is_active == True
    ).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
