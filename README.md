# JoyClub Associate

Production MLM & Direct Selling platform — Django REST API + React admin console.

See **[RUN.md](./RUN.md)** for full startup instructions.

## Quick start

```sh
# API
cd backend
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

# UI (new terminal)
npm run dev
```

- App: http://localhost:8080  
- API docs: http://localhost:8000/api/docs/  
- Login: `admin@joyclub.associate` / `admin123`  
- Root Sponsor: `JC00000001`

## Stack

- Backend: Django 5, DRF, JWT, Celery, Redis, PostgreSQL/SQLite
- Frontend: React, TypeScript, TanStack Router/Query, Tailwind
- Config-driven commissions, genealogy, wallets, KYC, deposits, withdrawals
