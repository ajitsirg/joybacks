#!/usr/bin/env python3
"""Deploy JoyClub Associate Docker stack to Hostinger VPS (joyclubs.in).

Auth (first match wins):
  1) DOVIX_SSH_PASSWORD env
  2) SSH key at ~/.ssh/sora_vps_key (or DOVIX_SSH_KEY path)

Usage (PowerShell):
  $env:DOVIX_SSH_PASSWORD = 'your-root-password'
  python scripts/deploy_vps.py
"""

from __future__ import annotations

import os
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("DOVIX_SSH_HOST", "69.62.82.172")
USER = os.environ.get("DOVIX_SSH_USER", "root")
PASSWORD = os.environ.get("DOVIX_SSH_PASSWORD", "")
KEY_PATH = Path(os.environ.get("DOVIX_SSH_KEY", str(Path.home() / ".ssh" / "sora_vps_key")))
REMOTE = os.environ.get("JOYCLUB_REMOTE_DIR", "/opt/joyclub")
DOMAIN = os.environ.get("JOYCLUB_DOMAIN", "joyclubs.in")
LEGACY_DOMAIN = os.environ.get("JOYCLUB_LEGACY_DOMAIN", "accounts.dovix.ai")
CERTBOT_EMAIL = os.environ.get("JOYCLUB_CERTBOT_EMAIL", "admin@joyclubs.in")

# NEVER pack or upload local DB / dump / fixture data to the server.
# Production Postgres lives in Docker volumes on the VPS only.
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "backend/.venv",
    "mobile",
    "dist",
    ".output",
    ".tanstack",
    ".nitro",
    "backend/media",
    "backend/staticfiles",
    "__pycache__",
    "agent-transcripts",
    "backups",
    "pgdata",
    "postgres-data",
}

# Local DB dumps / fixtures — blocked from every deploy tarball.
EXCLUDE_DB_NAMES = {
    "db.sqlite3",
    "_prod_data.json",
    "prod_data.json",
    "local_data.json",
    "dump.json",
    "data.json",
}
EXCLUDE_DB_SUFFIXES = (
    ".sqlite3",
    ".sqlite",
    ".db",
    ".sql",
    ".dump",
    ".pgdump",
    ".backup",
    ".bak",
    ".apk",
)


def connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Prefer key files that work with Paramiko on Windows
    key_candidates = [
        Path(os.environ.get("DOVIX_SSH_KEY", "")),
        Path.home() / ".ssh" / "sora_vps_key",
        Path.home() / ".ssh" / "joyclub_deploy",
        KEY_PATH,
    ]
    for key_path in key_candidates:
        if not key_path or not key_path.exists() or not key_path.is_file():
            continue
        try:
            pkey = paramiko.Ed25519Key.from_private_key_file(str(key_path))
            client.connect(
                HOST,
                username=USER,
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
                timeout=30,
            )
            print(f"SSH ok via key {key_path}")
            return client
        except Exception as exc:
            print(f"Key failed {key_path.name}: {type(exc).__name__}")
    if PASSWORD:
        client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, allow_agent=False, timeout=30)
        print("SSH ok via password")
        return client
    raise SystemExit(
        "No SSH auth available.\n"
        "Set DOVIX_SSH_PASSWORD or place a working key at ~/.ssh/sora_vps_key"
    )


def run(client: paramiko.SSHClient, cmd: str, check: bool = True) -> str:
    print(f"$ {cmd}")
    _, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip())
    if check and code != 0:
        raise SystemExit(f"Command failed ({code}): {cmd}")
    return out


def is_local_db_artifact(path: Path, rel: str) -> bool:
    """True if this file is local DB / dump data and must never reach the server."""
    name = path.name
    lower = name.lower()
    if name in EXCLUDE_DB_NAMES or lower in EXCLUDE_DB_NAMES:
        return True
    if name.startswith("db.sqlite3"):
        return True
    # Allow intentional public downloads (APKs); block everything else matching dump suffixes.
    if "downloads" in rel.split("/"):
        return False
    if lower.endswith(EXCLUDE_DB_SUFFIXES):
        return True
    if "/fixtures/" in f"/{rel}/" and lower.endswith(".json"):
        # Never ship local fixture dumps; keep only tracked empty/schema fixtures if needed later.
        if any(tag in lower for tag in ("prod", "local", "dump", "backup", "demo_data")):
            return True
    return False


def pack() -> Path:
    tmp = Path(tempfile.mkstemp(suffix=".tar.gz")[1])
    print(f"Packing project → {tmp} (code only; local DB/dumps excluded)")
    skipped_db = 0
    with tarfile.open(tmp, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            parts = rel.split("/")
            if any(p in EXCLUDE_DIRS or p.endswith(".pyc") for p in parts):
                continue
            if is_local_db_artifact(path, rel):
                skipped_db += 1
                continue
            tar.add(path, arcname=rel)
    if skipped_db:
        print(f"Excluded {skipped_db} local DB/dump file(s) from upload")
    return tmp


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not (ROOT / ".env.production").exists():
        raise SystemExit("Missing .env.production — copy from .env.production.example")

    client = connect()
    print(f"Connected to {USER}@{HOST}")

    # Ensure deploy key is installed for future key-based deploys
    pub = Path.home() / ".ssh" / "sora_vps_key.pub"
    if pub.exists():
        key = pub.read_text(encoding="utf-8").strip()
        run(
            client,
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && "
            f"grep -qxF '{key}' ~/.ssh/authorized_keys || echo '{key}' >> ~/.ssh/authorized_keys",
            check=False,
        )

    run(client, f"mkdir -p {REMOTE} {REMOTE}/backups")
    archive = pack()
    remote_tar = f"/tmp/joyclub-deploy.tar.gz"
    print(f"Uploading {archive} → {remote_tar}")
    sftp = client.open_sftp()
    sftp.put(str(archive), remote_tar)
    sftp.close()
    try:
        archive.unlink(missing_ok=True)
    except OSError:
        pass

    # Pre-deploy DB backup (Docker volume data is never wiped by this deploy).
    # Keep /opt/joyclub/backups across code refreshes — never delete live data.
    run(
        client,
        f"if [ -f {REMOTE}/docker-compose.prod.yml ] && [ -f {REMOTE}/.env.production ]; then "
        f"chmod +x {REMOTE}/scripts/backup_db_daily.sh 2>/dev/null || true; "
        f"JOYCLUB_REMOTE_DIR={REMOTE} bash {REMOTE}/scripts/backup_db_daily.sh || "
        f"echo 'Pre-deploy backup skipped (first deploy or db not up yet)'; "
        f"fi",
        check=False,
    )

    # Refresh code only — preserve backups/ and Docker named volumes (pgdata, media).
    run(
        client,
        # Preserve backups/ and public/ (uploaded PDFs, APKs) across deploys.
        f"find {REMOTE} -mindepth 1 -maxdepth 1 ! -name backups ! -name public -exec rm -rf {{}} + && "
        f"tar -xzf {remote_tar} -C {REMOTE} && rm -f {remote_tar} && "
        f"mkdir -p {REMOTE}/backups && "
        f"sed -i 's/\\r$//' {REMOTE}/scripts/backup_db_daily.sh && "
        f"chmod +x {REMOTE}/scripts/backup_db_daily.sh",
    )
    run(client, "command -v docker >/dev/null || (curl -fsSL https://get.docker.com | sh)")
    run(client, "systemctl enable --now docker || true", check=False)

    # Code/image rebuild only — migrate is additive; never flush/drop volumes.
    # NEVER push local DB, loaddata fixtures, seed_local_demo, or restore dumps onto production.
    run(
        client,
        f"cd {REMOTE} && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build",
    )
    # Safety: confirm no local dump artifacts landed in the app dir (ignore server backups/).
    run(
        client,
        f"find {REMOTE} -maxdepth 3 \\( -name 'db.sqlite3*' -o -name '_prod_data.json' "
        f"-o -name '*.pgdump' -o -name 'local_data.json' \\) "
        f"! -path '{REMOTE}/backups/*' -print 2>/dev/null | head -20; "
        f"echo 'DB_ARTIFACT_SCAN_DONE'",
        check=False,
    )

    # Install daily 02:00 backup cron (idempotent). Backups accumulate; never auto-pruned.
    cron_line = f"0 2 * * * JOYCLUB_REMOTE_DIR={REMOTE} /bin/bash {REMOTE}/scripts/backup_db_daily.sh"
    run(
        client,
        "crontab -l 2>/dev/null | grep -v backup_db_daily.sh > /tmp/joyclub.cron || true; "
        f"echo '{cron_line}' >> /tmp/joyclub.cron; "
        "crontab /tmp/joyclub.cron && rm -f /tmp/joyclub.cron && crontab -l | grep backup_db_daily || true",
        check=False,
    )

    # Post-deploy backup snapshot
    run(
        client,
        f"JOYCLUB_REMOTE_DIR={REMOTE} bash {REMOTE}/scripts/backup_db_daily.sh || true",
        check=False,
    )

    print("Waiting for API...")
    for _ in range(40):
        out = run(client, "curl -sf http://127.0.0.1:18001/api/v1/app/latest/ || true", check=False)
        if "version_code" in out or "joyclub" in out.lower():
            print("API is responding")
            break
        time.sleep(6)
    else:
        run(client, f"cd {REMOTE} && docker compose -f docker-compose.prod.yml logs --tail=80 api", check=False)

    http_conf = f"{REMOTE}/deploy/nginx/{DOMAIN}.http.conf"
    ssl_conf = f"{REMOTE}/deploy/nginx/{DOMAIN}.conf"

    # Nginx HTTP bootstrap then certbot (www + apex when using joyclubs.in)
    run(client, f"test -f {http_conf}")
    run(client, f"cp {http_conf} /etc/nginx/sites-available/{DOMAIN}")
    run(client, f"ln -sfn /etc/nginx/sites-available/{DOMAIN} /etc/nginx/sites-enabled/{DOMAIN}")

    # Keep legacy domain serving the same stack during DNS cutover (do not redirect yet)
    if LEGACY_DOMAIN and LEGACY_DOMAIN != DOMAIN:
        legacy_ssl = f"{REMOTE}/deploy/nginx/{LEGACY_DOMAIN}.conf"
        run(
            client,
            f"if [ -f {legacy_ssl} ] && [ -f /etc/letsencrypt/live/{LEGACY_DOMAIN}/fullchain.pem ]; then "
            f"cp {legacy_ssl} /etc/nginx/sites-available/{LEGACY_DOMAIN} && "
            f"ln -sfn /etc/nginx/sites-available/{LEGACY_DOMAIN} /etc/nginx/sites-enabled/{LEGACY_DOMAIN}; "
            f"fi",
            check=False,
        )

    run(client, "nginx -t && systemctl reload nginx")

    certbot_domains = f"-d {DOMAIN}"
    if DOMAIN == "joyclubs.in":
        certbot_domains = f"-d {DOMAIN} -d www.{DOMAIN}"

    run(
        client,
        f"certbot --nginx {certbot_domains} --non-interactive --agree-tos -m {CERTBOT_EMAIL} --redirect || true",
        check=False,
    )
    # Prefer full SSL template once certs exist
    run(
        client,
        f"test -f /etc/letsencrypt/live/{DOMAIN}/fullchain.pem && "
        f"cp {ssl_conf} /etc/nginx/sites-available/{DOMAIN} && "
        f"nginx -t && systemctl reload nginx || true",
        check=False,
    )

    run(client, "curl -sI http://127.0.0.1:18002/ | head -8", check=False)
    run(client, f"curl -skI https://{DOMAIN}/ | head -12", check=False)
    run(client, f"curl -skI https://{DOMAIN}/admin/ | head -12", check=False)
    run(client, "curl -sf http://127.0.0.1:18001/api/v1/app/latest/ || true", check=False)

    # Verify superuser
    run(
        client,
        f"cd {REMOTE} && docker compose -f docker-compose.prod.yml exec -T api "
        f"python manage.py shell -c \"from django.contrib.auth import get_user_model; "
        f"U=get_user_model(); u=U.objects.filter(username='Ajit').first() or U.objects.filter(email__icontains='ajit').first(); "
        f"print('SUPERUSER', u.email if u else 'MISSING', 'staff', getattr(u,'is_staff',None), 'super', getattr(u,'is_superuser',None))\"",
        check=False,
    )

    print(f"\nDone. Open https://{DOMAIN}/")
    print(f"Django admin: https://{DOMAIN}/admin/")
    print("Login email: ajit@accounts.dovix.ai  |  password: ajit@123")
    print(f"DNS required: {DOMAIN} A → {HOST} (and www CNAME/A to same)")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
