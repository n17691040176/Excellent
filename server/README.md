# Excellent App Backend

## Run

```powershell
cd D:\Excellent\server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app\db\init_db.py
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Default admin

- phone: `18800000000`
- password: `Admin@123`

## Main files

- `server/app/main.py`
- `server/app/api/v1/`
- `server/app/models/`
- `server/app/services/`
- `server/sql/schema.sql`

## Notes

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Seed runs during app startup

## Legacy import

- Legacy user raw fields are preserved in `user_legacy_profiles`
- Current app only uses `users` business fields; unused legacy fields are not exposed by default
- Admin can inspect one imported user's raw legacy data via `GET /api/v1/admin/users/{user_id}/legacy-profile`
