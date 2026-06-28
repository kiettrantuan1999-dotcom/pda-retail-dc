from datetime import datetime, time
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.tables import AuditLog


def _clean(value: str) -> str:
    return (value or "").strip()


def search_audit_logs(
    db: Session,
    q: str = "",
    operation: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 200,
):
    query = db.query(AuditLog)

    q = _clean(q)
    operation = _clean(operation).upper()

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                AuditLog.reference_no.ilike(like),
                AuditLog.pallet_id.ilike(like),
                AuditLog.location_id.ilike(like),
                AuditLog.sku.ilike(like),
                AuditLog.barcode.ilike(like),
                AuditLog.user_name.ilike(like),
                AuditLog.remark.ilike(like),
            )
        )

    if operation:
        query = query.filter(AuditLog.operation == operation)

    if date_from:
        dt_from = datetime.combine(datetime.strptime(date_from, "%Y-%m-%d").date(), time.min)
        query = query.filter(AuditLog.created_at >= dt_from)

    if date_to:
        dt_to = datetime.combine(datetime.strptime(date_to, "%Y-%m-%d").date(), time.max)
        query = query.filter(AuditLog.created_at <= dt_to)

    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


def get_operation_options():
    return ["GR", "PUTAWAY", "PACK", "COUNT", "ADJUST"]
