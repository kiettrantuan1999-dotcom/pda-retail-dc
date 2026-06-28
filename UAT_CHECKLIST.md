# UAT CHECKLIST - Supra WES v1.0

## 1. Chuẩn bị

```bash
python scripts/init_db.py
python scripts/seed_all.py
python -m uvicorn app.main:app --reload
```

Đăng nhập test:

- Admin: `admin / 123456`
- Supervisor: `supervisor1 / 123456`
- Worker: `worker1 / 123456`

## 2. Core/Login

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Login admin | Đăng nhập `admin/123456` | Vào được trang chủ, thấy menu quản trị |
| Login worker | Đăng nhập `worker1/123456` | Vào được trang chủ, không thấy menu quản trị |
| Sai mật khẩu | Nhập sai password | Không đăng nhập được |

## 3. GR - Nhận hàng

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| GR PO test | Vào GR, nhập `PO_TEST_001` | PO hợp lệ |
| Scan barcode | Scan `899000000001` | Hiển thị SKU/product |
| Confirm GR | Nhập PA và số lượng | Ghi nhận GR, tạo task cất hàng |

## 4. Put Away - Cất hàng

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Xem task | Vào Put Away | Thấy PA chờ cất hàng |
| Cất hàng PA | Chọn/scan PA `PA-SAMPLE-001`, location `A01-001` | Ghi nhận put away |
| Tồn kho | Tra cứu tồn sau cất | Tồn tăng đúng vị trí |

## 5. Pack - Đóng hàng

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Mở DO | Vào Pack, nhập `DO001` | Hiển thị thông tin DO |
| Confirm pack | Xác nhận đóng hàng | Trạng thái chuyển đã đóng/giao dịch được ghi log |

## 6. Inventory - Kiểm kê

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Tra cứu tồn | Tìm SKU `SKU001` | Hiển thị tồn tại location |
| Tạo count | Tạo phiếu kiểm kê | Có count header/detail |
| Nhập count | Nhập số lượng thực tế | Lưu count qty và variance |
| Duyệt count | Admin/Supervisor duyệt | Tồn được điều chỉnh nếu lệch |

## 7. Audit - Truy vết

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Mở audit | Vào `/audit` | Màn hình truy vết mở được |
| Filter SKU | Tìm `SKU001` | Chỉ hiện log liên quan |
| Filter thao tác | Chọn Nhận hàng/Cất hàng/Đóng hàng | Dữ liệu lọc đúng |
| Export | Bấm Xuất dữ liệu | Tải file CSV, tiếng Việt không lỗi font |

## 8. Admin - Người dùng

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Xem user | Vào `/admin/users` | Thấy danh sách user |
| Tạo user | Tạo user mới | User đăng nhập được |
| Khóa user | Set inactive | User không đăng nhập được |
| Reset password | Reset về `123456` | Đăng nhập bằng password mới được |

## 9. Admin - Quyền

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Xem quyền | Vào `/admin/roles` | Thấy quyền theo Admin/Supervisor/Worker |
| Worker truy cập admin | Đăng nhập worker và vào `/admin/users` | Bị chặn/redirect |

## 10. Admin - Cấu hình

| Case | Bước kiểm thử | Kết quả kỳ vọng |
|---|---|---|
| Mở settings | Vào `/admin/settings` | Hiển thị cấu hình hệ thống |
| Sửa setting | Đổi Tên kho hoặc Prefix PA | Lưu thành công |

## 11. Kết luận UAT

| Nội dung | Kết quả |
|---|---|
| Tất cả route chính mở được | ☐ Pass / ☐ Fail |
| Data test chạy được | ☐ Pass / ☐ Fail |
| Worker không vào admin/audit trái quyền | ☐ Pass / ☐ Fail |
| Audit ghi đủ thao tác chính | ☐ Pass / ☐ Fail |
| Export mở được bằng Excel | ☐ Pass / ☐ Fail |
