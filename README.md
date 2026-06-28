# Supra WES v1.0

Supra WES là ứng dụng PDA/WES nội bộ cho kho Retail DC, dùng FastAPI + SQLAlchemy + giao diện web tối ưu cho điện thoại/PDA.

## 1. Phạm vi v1.0

### Nghiệp vụ đã có

| Module | Đường dẫn | Mục đích |
|---|---|---|
| Đăng nhập / phân quyền | `/login` | Worker / Supervisor / Admin |
| Trang chủ PDA | `/` | Menu nghiệp vụ theo quyền |
| Nhận hàng | `/gr` | Scan PO, barcode, PA, số lượng |
| Cất hàng | `/putaway` | Scan PA/location, xác nhận cất hàng |
| Picking | `/picking` | Tạo/hiển thị phiếu picking từ DO |
| Đóng hàng | `/pack` | Xác nhận đóng hàng theo DO/Picking |
| Kiểm kê | `/inventory` | Tra cứu tồn, tạo phiếu kiểm kê, nhập count, duyệt điều chỉnh |
| Dashboard Supervisor | `/supervisor/dashboard` | KPI vận hành cơ bản |
| Audit | `/audit` | Truy vết thao tác và xuất dữ liệu |
| Quản lý User | `/admin/users` | Tạo/sửa/khóa user, reset mật khẩu |
| Xem quyền | `/admin/roles` | Xem quyền hiện tại theo vai trò |
| Cấu hình hệ thống | `/admin/settings` | Cấu hình kho, prefix PA, audit, mật khẩu reset |

### Module đã skip để làm sau

- Sprint 8: Warehouse Monitor
- Sprint 9: Reporting
- Quyền động trong DB: chưa làm, quyền vẫn quản lý trong `app/core/permissions.py`.

## 2. Cấu trúc thư mục

```text
app/
  core/               # config, security, permission
  db/                 # SQLAlchemy session
  middleware/         # error logging middleware
  models/             # ORM model
  routes/             # FastAPI router
  services/           # business logic
  static/             # CSS/JS
  templates/          # HTML Jinja2
scripts/
  init_db.py          # tạo toàn bộ bảng
  seed_all.py         # seed dữ liệu test chuẩn v1.0
  smoke_check.py      # kiểm tra nhanh app/db/router/model
  migrate_*.py        # migration theo sprint cũ
create_tables.py      # wrapper cũ, giữ lại để tương thích
run.py                # entrypoint chạy app nếu cần
requirements.txt
.env.example
UAT_CHECKLIST.md
PROJECT_STRUCTURE.md
```

## 3. Cài đặt local trên Windows

### 3.1 Tạo môi trường ảo

```bash
python -m venv venv
```

PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source venv/Scripts/activate
```

### 3.2 Cài thư viện

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3.3 Tạo file `.env`

Copy file mẫu:

```bash
cp .env.example .env
```

Ví dụ local SQLite:

```env
DATABASE_URL=sqlite:///./supra_wes.db
SECRET_KEY=dev-secret-change-me
APP_ENV=local
```

## 4. Khởi tạo database và data test

Chạy theo thứ tự:

```bash
python scripts/init_db.py
python scripts/seed_all.py
python scripts/smoke_check.py
```

Kết quả kỳ vọng:

```text
OK: database tables created
OK: v1.0 seed data completed
OK: smoke check passed
```

## 5. Chạy app

```bash
python -m uvicorn app.main:app --reload
```

Mở trình duyệt:

```text
http://127.0.0.1:8000
```

Cho điện thoại/PDA trong cùng mạng LAN:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Sau đó mở bằng IP laptop, ví dụ:

```text
http://192.168.1.20:8000
```

## 6. Tài khoản test

| User | Password | Role |
|---|---|---|
| admin | 123456 | admin |
| supervisor1 | 123456 | supervisor |
| worker1 | 123456 | worker |

## 7. Dữ liệu test chính

| Loại | Mã test |
|---|---|
| PO nhận hàng | `PO_TEST_001` |
| Barcode test | `899000000001`, `899000000002`, `899000000003` |
| PA chờ cất hàng | `PA-SAMPLE-001`, `PA-SAMPLE-002` |
| Location | `A01-001`, `A01-002`, `A02-001`, `PACK-STAGE` |
| DO đóng hàng | `DO001`, `DO002` |
| Count No mẫu | `COUNT_TEST_001` |

## 8. Lệnh kiểm tra nhanh

```bash
python scripts/smoke_check.py
```

Script này kiểm tra:

- Import app chính.
- Import router quan trọng.
- Import model chính.
- Kết nối database.
- Bảng tồn tại.
- Có user admin.

## 9. Deploy Railway

Checklist tối thiểu:

1. Cấu hình biến môi trường:

```env
DATABASE_URL=<database-url-production>
SECRET_KEY=<secret-production>
APP_ENV=production
```

2. Cài dependency từ `requirements.txt`.
3. Start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Chạy migration/seed nếu cần theo môi trường production.

## 10. Ghi chú vận hành

- Không commit `venv/`, `.env`, `__pycache__/`, file `.db` local.
- Mật khẩu reset mặc định hiện là `123456`, có thể đổi trong `/admin/settings`.
- Quyền user hiện vẫn nằm trong `app/core/permissions.py` để đơn giản và an toàn cho MVP.
- Audit export đang xuất CSV có BOM UTF-8 để Excel đọc tiếng Việt đúng.
