# PDA Retail DC Execution App v2

FastAPI + Supabase PostgreSQL + Bootstrap PDA UI. Không cần Docker.

## Chạy local

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Tạo `.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
SECRET_KEY=KietRetailDC2026@FastAPI
APP_ENV=local
```

Nếu direct DB bị lỗi DNS/5432, dùng Supabase Transaction Pooler.

```powershell
python create_tables.py
python seed_data.py
python run.py
```

Mở: http://localhost:8000

Login: `admin / 123456` hoặc `worker1 / 123456`

## Module có sẵn

- Login
- Home
- GR
- Put Away
- Pack
- Inventory Check
- Audit

## Test nhanh

GR: barcode `899000000001`, qty `10`.

Put Away DONE: PA `PA-SAMPLE-001`, location `A02-001`, qty `20`.

Put Away PARTIAL: PA `PA-SAMPLE-002`, location `A02-002`, qty `5`.

Pack: DO `DO001`, barcode `899000000001`, qty `5`.

Audit: location `A01-001`, chọn SKU, nhập physical qty.

## Deploy Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```env
DATABASE_URL=...
SECRET_KEY=...
APP_ENV=production
```

## Ghi chú

Bản v2 là nền sạch hơn bản demo, có service layer, transaction rollback, row lock `with_for_update()` ở inbound/inventory/do_detail. Các phần cần làm tiếp: Alembic migration, import/export Excel hoàn chỉnh, idempotency key chống double scan tuyệt đối, role permission chi tiết.
