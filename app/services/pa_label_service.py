from datetime import datetime
import random

PA_PREFIX = "PADCDN"


def generate_pa_code(prefix: str = PA_PREFIX) -> str:
    """Sinh mã PA: PADCDN + DDMMYYYY + random 4 số."""
    today = datetime.now().strftime("%d%m%Y")
    suffix = random.randint(1000, 9999)
    return f"{prefix}{today}{suffix}"


def generate_pa_labels(qty: int, prefix: str = PA_PREFIX) -> list[dict]:
    qty = int(qty or 0)

    if qty <= 0:
        raise ValueError("Số tem cần in phải lớn hơn 0")

    if qty > 200:
        raise ValueError("Mỗi lần chỉ nên in tối đa 200 tem PA")

    codes: set[str] = set()
    while len(codes) < qty:
        codes.add(generate_pa_code(prefix))

    return [{"code": code} for code in sorted(codes)]


# Backward compatible nếu route cũ còn import generate_pa_codes.
def generate_pa_codes(qty: int, prefix: str = PA_PREFIX) -> list[str]:
    return [x["code"] for x in generate_pa_labels(qty, prefix)]
