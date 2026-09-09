# New VPS deploy — change every item

Do **not** upload `backend/db.sqlite3`, `backups/`, or `*_prod_data.json`.
Staff / Super Admin must **never** be an associate.

Do **not** deploy until the fill-in block in §10 is complete.

## 1. Server access

| Item | What to set |
|---|---|
| SSH host / IP | New VPS IP |
| SSH user | usually `root` |
| SSH password or key | New password or new key (rotate old Hostinger password) |
| OS | Ubuntu 24.04 is fine |
| App folder | `/opt/joyclub` (or new path) |

```bash
export DOVIX_SSH_HOST=<NEW_IP>
export DOVIX_SSH_USER=root
export DOVIX_SSH_KEY=<path-to-key>          # or DOVIX_SSH_PASSWORD
export JOYCLUB_DOMAIN=<NEW_DOMAIN>
export JOYCLUB_LEGACY_DOMAIN=               # leave empty unless you have an old domain
export JOYCLUB_ENV_FILE=.env.production.<client>
export JOYCLUB_CERTBOT_EMAIL=<YOUR_EMAIL>
export JOYCLUB_REMOTE_DIR=/opt/joyclub
python3 scripts/deploy_vps.py
```

## 2. Domain + DNS

Set these **before** HTTPS:

| Item | What to set |
|---|---|
| Domain | e.g. `app.clientdomain.com` |
| DNS A record | domain → new VPS IP |
| WWW (optional) | CNAME or A to same IP |

Nginx is generated from `deploy/nginx/_template.http.conf` and `deploy/nginx/_template.conf`.
Do **not** reuse `demo.srv1906249.hstgr.cloud` or copy joyclubs.in files as-is.

In both files the renderer sets:

- `server_name` → new domain
- HTTP → HTTPS redirect host
- SSL paths: `/etc/letsencrypt/live/<NEW_DOMAIN>/...`
- Django admin location: must match `DJANGO_ADMIN_PATH`

Keep these proxy ports unless you change Docker:

- API `127.0.0.1:18001`
- Web `127.0.0.1:18002`

## 3. New env file `.env.production.<client>`

Copy `.env.production.example` and change **all** secrets. See that file for the full key list.

`POSTGRES_PASSWORD` must match `DATABASE_URL` or the API will 502.

## 4. Logins (two different accounts)

| Who | Email / user | Password | Associate? |
|---|---|---|---|
| Frontend Super Admin | `admin@joyclub.associate` (or new staff email) | change from `admin123` | **Never** |
| Django admin | `DJANGO_ADMIN_EMAIL` | `DJANGO_ADMIN_PASSWORD` | **Never** |
| Company root associate | `JOY00000001` / `root@joyclub.associate` | change from `admin123` | Yes — a member, not staff |

After deploy, set company flags on:

- `show_income_section`
- `show_income_referral`
- `show_income_sp_profit` (menu label is S.H. Profit)
- `show_platinum_package`
- `show_silver_package`

## 5. Django admin URL

`DJANGO_ADMIN_PATH` and nginx `location /<PATH>/` must be the **same** new token.

Example only (do not reuse on a client server):

`8f3c1a9e2b74d0c6a5e18f42b9d37c01e6a4f8b2c0d1957e`

Live URL: `https://<NEW_DOMAIN>/<DJANGO_ADMIN_PATH>/`

## 6. License (one server)

After first boot:

1. `python manage.py license_fingerprint`
2. Put the value in `LICENSE_FINGERPRINT`
3. Issue + activate a license for this server only

Another install needs a new code from you.

## 7. Product rules already in code (do not undo)

- Home page = login
- No Audit Log / QR / News / Business Report in admin menu
- Associate detail: no Last login / Last IP
- Reward amounts = official poster (₹30,000 / ₹75,000 / …)
- S.P. Profit label = S.H. Profit
- Fund Transfer asks login password every time
- Dashboard pending counts refresh ~every 2 seconds
- Staff / Super Admin can never be an associate

## 8. First deploy steps

1. DNS A record live
2. New `.env.production.<client>` + generated nginx files
3. `python scripts/deploy_vps.py` with the env vars in §1
4. Confirm site: `https://<NEW_DOMAIN>/` (login)
5. Confirm API: `https://<NEW_DOMAIN>/api/v1/config/runtime/`
6. Confirm Django admin token URL
7. `seed_joyclub` / create staff + root associate
8. Activate license
9. Change all default passwords
10. Optional: load a dump **only** if this client should get old pulled data (never upload local sqlite)

## 9. Never upload

- `backend/db.sqlite3`
- `backups/`
- `*_prod_data.json`
- old `.env.production` / `.env.production.demo` as-is

## 10. Fill this block before deploy

```
VPS_IP=
SSH_USER=root
SSH_PASSWORD_OR_KEY=
DOMAIN=
CERTBOT_EMAIL=
DJANGO_ADMIN_EMAIL=
DJANGO_ADMIN_PASSWORD=
FRONTEND_SUPERADMIN_EMAIL=
FRONTEND_SUPERADMIN_PASSWORD=
DB_PASSWORD=
SECRET_KEY=
LICENSE_CONTACT_EMAIL=
LOAD_OLD_BACKUP=yes/no
```

Send the filled block when the new VPS and domain are ready. Deploy only after those values are filled.
