from datetime import datetime
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def now_vn() -> datetime:
    """Return naive Vietnam local datetime for DB DateTime columns.

    The project stores DateTime columns as naive timestamps. On Railway/Postgres,
    datetime.utcnow() records UTC, so scan logs display 7 hours behind Vietnam.
    This helper stores Vietnam wall-clock time directly to keep operation logs,
    audit logs, GR/Put Away/Pack/Staging times aligned with warehouse users.
    """
    return datetime.now(VIETNAM_TZ).replace(tzinfo=None)


def today_vn():
    return now_vn().date()


def format_vn(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if not dt:
        return ""
    return dt.strftime(fmt)
