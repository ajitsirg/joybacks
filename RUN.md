# JoyClub Associate — Run Guide

## 1) Backend (Django API)

```bash
cd backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_joyclub
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

- API docs: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/
- Admin login: `admin@joyclub.associate` / `admin123`
- Root Sponsor ID: `JC00000001`

## 2) Frontend

```bash
npm i --legacy-peer-deps
npm run dev
```

Open http://localhost:8080 and sign in with the admin account.

## 3) Docker (Postgres + Redis + API)

```bash
docker compose up --build
```

Set `DATABASE_URL=postgres://joyclub:joyclub@db:5432/joyclub` in `backend/.env`.

## Product modules live

- Auth JWT + RBAC
- Associates + mandatory sponsor + OTP register (`/register`)
- Genealogy tree (expandable)
- Wallets + ledger + admin fund transfer
- KYC / Deposits / Withdrawals (approve runs commissions)
- Level/Performance/ROI/Reward config in DB
- Dashboard + business report (real-time API)
- CMS news/help/QR, notifications, audit log

## 4) Flutter mobile app

```bash
cd mobile
flutter pub get
flutter run -d windows
# or: flutter run -d chrome
```

Includes login/join with KYC uploads, waiting for lead approval, Team Approvals, dashboard, tree, wallets, income, deposit & withdraw.

See `mobile/README.md` for device API URL (`--dart-define=API_BASE=...`).
