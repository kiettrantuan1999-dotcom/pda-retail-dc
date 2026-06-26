# Supra WES - Sprint 1 Core Platform

## Chức năng

- Login tiếng Việt
- Role: worker / supervisor / admin
- Permission nền
- Dashboard quản lý nền
- Nhật ký thao tác
- Nhật ký lỗi
- User list
- Model mới cho pallet_header / pallet_detail
- Chưa hoàn thiện nghiệp vụ Nhận hàng/Cất hàng/Đóng hàng. Các module này sẽ làm ở Sprint 2+.

## Chạy local

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python create_tables.py
python seed_core.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Login

```text
admin / 123456
worker1 / 123456
supervisor1 / 123456
```

## Push deploy

```bash
git add .
git commit -m "Sprint 1 core platform"
git push
```

Railway sẽ tự deploy.
