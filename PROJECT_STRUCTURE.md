# PROJECT_STRUCTURE - Supra WES v1.0

## Nguyên tắc tổ chức code

```text
Route nhận request
  ↓
Service xử lý nghiệp vụ
  ↓
Model/DB ghi dữ liệu
  ↓
Template hiển thị giao diện
```

## Thư mục chính

| Thư mục/File | Vai trò |
|---|---|
| `app/main.py` | Khởi tạo FastAPI, middleware, static file, include router |
| `app/core/config.py` | Đọc biến môi trường |
| `app/core/security.py` | Hash/check password |
| `app/core/permissions.py` | Phân quyền hard-code theo role |
| `app/db/session.py` | SQLAlchemy engine/session |
| `app/models/tables.py` | Toàn bộ ORM model |
| `app/routes/` | Router theo module |
| `app/services/` | Logic nghiệp vụ |
| `app/templates/` | Giao diện Jinja2 |
| `app/static/` | CSS/JS frontend |
| `scripts/` | Migration, seed, smoke check |

## Module route chính

| Module | Router | Template |
|---|---|---|
| Home/Auth | `pages.py`, `auth.py` | `home.html`, `login.html` |
| GR | `api.py` / service liên quan | `gr.html` |
| Put Away | `putaway.py` | `putaway/*` |
| Picking | `picking.py` | `picking/*` |
| Pack | `pack.py` | `pack/*` |
| Inventory | `inventory.py` | `inventory/*` |
| Supervisor | `supervisor.py` | `supervisor/dashboard.html` |
| Audit | `audit.py` | `audit.html` |
| Admin | `admin.py` | `admin/*` |

## Bảng dữ liệu chính

| Nhóm | Bảng |
|---|---|
| User/Role | `app_user`, `app_role`, `app_permission`, `role_permission` |
| Master | `product_master`, `location_master`, `sku_master`, `supplier_master` |
| Inbound | `po_header`, `po_detail`, `pallet_header`, `pallet_detail`, `inbound_queue`, `gr_log`, `putaway_log` |
| Inventory | `inventory_balance`, `inventory_count_header`, `inventory_count_detail`, `inventory_adjustment_log` |
| Outbound | `do_detail`, `picking_header`, `picking_detail`, `pack_header`, `pack_log` |
| Trace | `audit_log`, `operation_log`, `error_log` |
| Admin | `system_setting` |

## Quy tắc khi thêm sprint mới

1. Không tạo layer mới nếu không cần.
2. Ưu tiên pattern: `routes -> services -> models`.
3. UI tiếng Việt 100% cho người vận hành.
4. Mọi nghiệp vụ quan trọng phải ghi `AuditLog` hoặc `OperationLog`.
5. File migration/seed phải thêm root path bằng `sys.path` để chạy được từ root project.
6. Không đưa `venv`, `.env`, cache, database local vào zip/git.
