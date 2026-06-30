from datetime import datetime, time

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.tables import (
    PoDetail,
    PalletDetail,
    PickingHeader,
    PackHeader,
    InventoryBalance,
    OperationLog,
    ErrorLog,
    GrLog,
    PutawayLog,
)


def _hom_nay():
    today = datetime.now().date()
    return (
        datetime.combine(today, time.min),
        datetime.combine(today, time.max),
    )


def _dem_an_toan(db: Session, model, *dieu_kien):
    try:
        query = db.query(func.count()).select_from(model)

        for dk in dieu_kien:
            query = query.filter(dk)

        return query.scalar() or 0

    except Exception:
        return 0


def _tong_an_toan(db: Session, cot, *dieu_kien):
    try:
        query = db.query(func.coalesce(func.sum(cot), 0))

        for dk in dieu_kien:
            query = query.filter(dk)

        return query.scalar() or 0

    except Exception:
        return 0
def _phut_cho(thoi_gian):
    if not thoi_gian:
        return 0

    try:
        return int((datetime.now() - thoi_gian).total_seconds() / 60)
    except Exception:
        return 0


def _dinh_dang_thoi_gian_cho(so_phut):
    if so_phut < 60:
        return f"{so_phut} phút"

    so_gio = so_phut // 60
    phut_le = so_phut % 60

    if phut_le == 0:
        return f"{so_gio} giờ"

    return f"{so_gio} giờ {phut_le} phút"


def lay_du_lieu_bang_dieu_khien(db: Session):
    dau_ngay, cuoi_ngay = _hom_nay()

    # =========================
    # NHẬN HÀNG
    # =========================

    gr_dang_cho = _dem_an_toan(
        db,
        PoDetail,
        PoDetail.status == "WAIT_GR",
    )

    gr_hoan_thanh_hom_nay = _dem_an_toan(
        db,
        GrLog,
        GrLog.gr_time >= dau_ngay,
        GrLog.gr_time <= cuoi_ngay,
    )

    # =========================
    # CẤT HÀNG
    # =========================

    cat_hang_dang_cho = _dem_an_toan(
        db,
        PalletDetail,
        PalletDetail.status.in_(["WAIT_PUTAWAY", "PARTIAL"]),
    )

    cat_hang_hoan_thanh_hom_nay = _dem_an_toan(
        db,
        PutawayLog,
        PutawayLog.putaway_time >= dau_ngay,
        PutawayLog.putaway_time <= cuoi_ngay,
    )

    # =========================
    # LẤY HÀNG
    # =========================

    lay_hang_dang_cho = _dem_an_toan(
        db,
        PickingHeader,
        PickingHeader.status.in_(["WAIT_PICK", "PROCESSING"]),
    )

    lay_hang_hoan_thanh = _dem_an_toan(
        db,
        PickingHeader,
        PickingHeader.status.in_(["DONE", "PICKED"]),
    )

    # =========================
    # ĐÓNG HÀNG
    # =========================

    dong_hang_dang_cho = _dem_an_toan(
        db,
        PackHeader,
        PackHeader.status.in_(["WAIT", "WAIT_PACK", "PROCESSING", "PACKING"]),
    )

    dong_hang_hoan_thanh_hom_nay = _dem_an_toan(
        db,
        PackHeader,
        PackHeader.status.in_(["DONE", "PACKED"]),
        PackHeader.packed_at >= dau_ngay,
        PackHeader.packed_at <= cuoi_ngay,
    )

    # =========================
    # TỒN KHO
    # =========================

    tong_ton = _tong_an_toan(
        db,
        InventoryBalance.qty_onhand,
        InventoryBalance.qty_onhand > 0,
    )

    try:
        so_sku_co_ton = (
            db.query(func.count(func.distinct(InventoryBalance.sku)))
            .filter(InventoryBalance.qty_onhand > 0)
            .scalar()
            or 0
        )
    except Exception:
        so_sku_co_ton = 0

    tong_cong_viec_dang_cho = (
        gr_dang_cho
        + cat_hang_dang_cho
        + lay_hang_dang_cho
        + dong_hang_dang_cho
    )

    # =========================
    # LỖI HÔM NAY
    # =========================

    loi_hom_nay = _dem_an_toan(
        db,
        ErrorLog,
        ErrorLog.created_at >= dau_ngay,
        ErrorLog.created_at <= cuoi_ngay,
    )

    # =========================
    # BẢNG SỨC KHỎE KHO
    # =========================

    suc_khoe_kho = [
        {
            "hang_muc": "Tổng công việc đang chờ",
            "gia_tri": tong_cong_viec_dang_cho,
            "ghi_chu": "Tổng GR + Cất hàng + Lấy hàng + Đóng hàng đang chờ",
        },
        {
            "hang_muc": "Lỗi hôm nay",
            "gia_tri": loi_hom_nay,
            "ghi_chu": "Số lỗi hệ thống phát sinh trong ngày",
        },
        {
            "hang_muc": "Tổng tồn kho",
            "gia_tri": f"{tong_ton:,}",
            "ghi_chu": f"{so_sku_co_ton:,} SKU đang có tồn",
        },
        {
            "hang_muc": "Lần cập nhật cuối",
            "gia_tri": datetime.now().strftime("%H:%M:%S"),
            "ghi_chu": "Theo thời gian máy chủ local",
        },
    ]

    # =========================
    # BẢNG CHỈ SỐ VẬN HÀNH
    # =========================

    chi_so_van_hanh = [
        {
            "module": "Nhận hàng",
            "dang_cho": gr_dang_cho,
            "hoan_thanh_hom_nay": gr_hoan_thanh_hom_nay,
            "ghi_chu": "PO detail chờ nhận hàng",
        },
        {
            "module": "Cất hàng",
            "dang_cho": cat_hang_dang_cho,
            "hoan_thanh_hom_nay": cat_hang_hoan_thanh_hom_nay,
            "ghi_chu": "Pallet/SKU chờ cất hàng",
        },
        {
            "module": "Lấy hàng",
            "dang_cho": lay_hang_dang_cho,
            "hoan_thanh_hom_nay": lay_hang_hoan_thanh,
            "ghi_chu": "Phiếu lấy hàng",
        },
        {
            "module": "Đóng hàng",
            "dang_cho": dong_hang_dang_cho,
            "hoan_thanh_hom_nay": dong_hang_hoan_thanh_hom_nay,
            "ghi_chu": "Phiếu chờ đóng hàng",
        },
    ]

    # =========================
    # HOẠT ĐỘNG GẦN ĐÂY
    # =========================

    hoat_dong_gan_day = []

    try:
        logs = (
            db.query(OperationLog)
            .order_by(desc(OperationLog.created_at))
            .limit(20)
            .all()
        )

        for dong in logs:
            hoat_dong_gan_day.append(
                {
                    "thoi_gian": dong.created_at.strftime("%H:%M:%S") if dong.created_at else "",
                    "phan_he": dong.module_name or "",
                    "su_kien": dong.event_type or "",
                    "ma_tham_chieu": dong.reference_id or "",
                    "nguoi_dung": dong.user_name or "",
                    "trang_thai": dong.status or "",
                }
            )

    except Exception:
        hoat_dong_gan_day = []

    # =========================
    # THEO DÕI LỖI
    # =========================

    theo_doi_loi = []

    try:
        logs = (
            db.query(ErrorLog)
            .order_by(desc(ErrorLog.created_at))
            .limit(10)
            .all()
        )

        for dong in logs:
            theo_doi_loi.append(
                {
                    "thoi_gian": dong.created_at.strftime("%H:%M:%S") if dong.created_at else "",
                    "phan_he": dong.module_name or "",
                    "ham": dong.function_name or "",
                    "nguoi_dung": dong.user_name or "",
                    "noi_dung_loi": (dong.error_message or "")[:120],
                }
            )

    except Exception:
        theo_doi_loi = []

    # =========================
    # CÔNG VIỆC TỒN LÂU NHẤT
    # =========================

    cong_viec_ton_lau = []

    try:
        po_wait = (
            db.query(PoDetail)
            .filter(PoDetail.status == "WAIT_GR")
            .order_by(PoDetail.last_update.asc())
            .limit(10)
            .all()
        )

        for dong in po_wait:
            so_phut = _phut_cho(dong.last_update)
            cong_viec_ton_lau.append({
                "phan_he": "Nhận hàng",
                "ma_tham_chieu": dong.po_no,
                "trang_thai": dong.status,
                "thoi_gian_cho": _dinh_dang_thoi_gian_cho(so_phut),
                "so_phut": so_phut,
            })
    except Exception:
        pass

    try:
        putaway_wait = (
            db.query(PalletDetail)
            .filter(PalletDetail.status.in_(["WAIT_PUTAWAY", "PARTIAL"]))
            .order_by(PalletDetail.last_update.asc())
            .limit(10)
            .all()
        )

        for dong in putaway_wait:
            so_phut = _phut_cho(dong.last_update)
            cong_viec_ton_lau.append({
                "phan_he": "Cất hàng",
                "ma_tham_chieu": dong.pallet_id,
                "trang_thai": dong.status,
                "thoi_gian_cho": _dinh_dang_thoi_gian_cho(so_phut),
                "so_phut": so_phut,
            })
    except Exception:
        pass

    try:
        picking_wait = (
            db.query(PickingHeader)
            .filter(PickingHeader.status.in_(["WAIT_PICK", "PROCESSING"]))
            .order_by(PickingHeader.last_update.asc())
            .limit(10)
            .all()
        )

        for dong in picking_wait:
            so_phut = _phut_cho(dong.last_update)
            cong_viec_ton_lau.append({
                "phan_he": "Lấy hàng",
                "ma_tham_chieu": dong.picking_no,
                "trang_thai": dong.status,
                "thoi_gian_cho": _dinh_dang_thoi_gian_cho(so_phut),
                "so_phut": so_phut,
            })
    except Exception:
        pass

    try:
        pack_wait = (
            db.query(PackHeader)
            .filter(PackHeader.status.in_(["WAIT", "WAIT_PACK", "PROCESSING", "PACKING"]))
            .order_by(PackHeader.last_update.asc())
            .limit(10)
            .all()
        )

        for dong in pack_wait:
            so_phut = _phut_cho(dong.last_update)
            cong_viec_ton_lau.append({
                "phan_he": "Đóng hàng",
                "ma_tham_chieu": dong.picking_no,
                "trang_thai": dong.status,
                "thoi_gian_cho": _dinh_dang_thoi_gian_cho(so_phut),
                "so_phut": so_phut,
            })
    except Exception:
        pass

    cong_viec_ton_lau = sorted(
        cong_viec_ton_lau,
        key=lambda x: x["so_phut"],
        reverse=True,
    )[:10]

    # =========================
    # NĂNG SUẤT NHÂN VIÊN
    # =========================

    nang_suat_nhan_vien = {}

    try:
        gr_rows = (
            db.query(GrLog.user_name, func.count(GrLog.gr_id))
            .filter(GrLog.gr_time >= dau_ngay, GrLog.gr_time <= cuoi_ngay)
            .group_by(GrLog.user_name)
            .all()
        )

        for user_name, so_luong in gr_rows:
            ten = user_name or "KHÔNG XÁC ĐỊNH"
            nang_suat_nhan_vien.setdefault(
                ten,
                {"nhan_vien": ten, "nhan_hang": 0, "cat_hang": 0, "dong_hang": 0, "tong": 0},
            )
            nang_suat_nhan_vien[ten]["nhan_hang"] = so_luong or 0
    except Exception:
        pass

    try:
        putaway_rows = (
            db.query(PutawayLog.user_name, func.count(PutawayLog.putaway_id))
            .filter(PutawayLog.putaway_time >= dau_ngay, PutawayLog.putaway_time <= cuoi_ngay)
            .group_by(PutawayLog.user_name)
            .all()
        )

        for user_name, so_luong in putaway_rows:
            ten = user_name or "KHÔNG XÁC ĐỊNH"
            nang_suat_nhan_vien.setdefault(
                ten,
                {"nhan_vien": ten, "nhan_hang": 0, "cat_hang": 0, "dong_hang": 0, "tong": 0},
            )
            nang_suat_nhan_vien[ten]["cat_hang"] = so_luong or 0
    except Exception:
        pass

    try:
        pack_rows = (
            db.query(PackHeader.packed_by, func.count(PackHeader.pack_id))
            .filter(
                PackHeader.status.in_(["DONE", "PACKED"]),
                PackHeader.packed_at >= dau_ngay,
                PackHeader.packed_at <= cuoi_ngay,
            )
            .group_by(PackHeader.packed_by)
            .all()
        )

        for user_name, so_luong in pack_rows:
            ten = user_name or "KHÔNG XÁC ĐỊNH"
            nang_suat_nhan_vien.setdefault(
                ten,
                {"nhan_vien": ten, "nhan_hang": 0, "cat_hang": 0, "dong_hang": 0, "tong": 0},
            )
            nang_suat_nhan_vien[ten]["dong_hang"] = so_luong or 0
    except Exception:
        pass

    nang_suat_nhan_vien = list(nang_suat_nhan_vien.values())

    for dong in nang_suat_nhan_vien:
        dong["tong"] = dong["nhan_hang"] + dong["cat_hang"] + dong["dong_hang"]

    nang_suat_nhan_vien = sorted(
        nang_suat_nhan_vien,
        key=lambda x: x["tong"],
        reverse=True,
    )

    updated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Alias cho template dashboard cũ để tránh lỗi khi user chủ động tải dashboard.
    kpi_rows = [
        {
            "module": r.get("module", ""),
            "wait": r.get("dang_cho", 0),
            "done_today": r.get("hoan_thanh_hom_nay", 0),
            "note": r.get("ghi_chu", ""),
        }
        for r in chi_so_van_hanh
    ]
    recent_rows = [
        {
            "time": r.get("thoi_gian", ""),
            "module": r.get("phan_he", ""),
            "event": r.get("su_kien", ""),
            "reference": r.get("ma_tham_chieu", ""),
            "user": r.get("nguoi_dung", ""),
            "status": r.get("trang_thai", ""),
        }
        for r in hoat_dong_gan_day
    ]
    error_rows = [
        {
            "time": r.get("thoi_gian", ""),
            "module": r.get("phan_he", ""),
            "function": r.get("ham", ""),
            "user": r.get("nguoi_dung", ""),
            "error": r.get("noi_dung_loi", ""),
        }
        for r in theo_doi_loi
    ]

    return {
        "ngay_gio_cap_nhat": updated_at,
        "updated_at": updated_at,
        "suc_khoe_kho": suc_khoe_kho,
        "chi_so_van_hanh": chi_so_van_hanh,
        "hoat_dong_gan_day": hoat_dong_gan_day,
        "theo_doi_loi": theo_doi_loi,
        "cong_viec_ton_lau": cong_viec_ton_lau,
        "nang_suat_nhan_vien": nang_suat_nhan_vien,
        "kpi_rows": kpi_rows,
        "recent_rows": recent_rows,
        "error_rows": error_rows,
    }