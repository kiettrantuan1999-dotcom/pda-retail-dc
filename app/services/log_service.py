import json
import traceback
from typing import Any
from sqlalchemy.orm import Session
from app.models.tables import OperationLog, ErrorLog


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data or {}, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


def write_operation_log(
    db: Session,
    *,
    event_type: str,
    module_name: str,
    user_name: str = "",
    reference_type: str = "",
    reference_id: str = "",
    status: str = "SUCCESS",
    message: str = "",
    request_payload: Any = None,
    ip_address: str = "",
    device_info: str = "",
) -> None:
    db.add(OperationLog(
        event_type=event_type,
        module_name=module_name,
        user_name=user_name or "",
        reference_type=reference_type or "",
        reference_id=reference_id or "",
        status=status or "SUCCESS",
        message=message or "",
        request_payload=_safe_json(request_payload),
        ip_address=ip_address or "",
        device_info=device_info or "",
    ))


def write_error_log(
    db: Session,
    *,
    module_name: str = "",
    function_name: str = "",
    user_name: str = "",
    error: Exception | str = "",
    request_payload: Any = None,
    ip_address: str = "",
    device_info: str = "",
) -> None:
    if isinstance(error, Exception):
        error_message = str(error)
        stack_trace = traceback.format_exc()
    else:
        error_message = str(error)
        stack_trace = ""

    db.add(ErrorLog(
        module_name=module_name or "",
        function_name=function_name or "",
        user_name=user_name or "",
        error_message=error_message,
        stack_trace=stack_trace,
        request_payload=_safe_json(request_payload),
        ip_address=ip_address or "",
        device_info=device_info or "",
    ))
