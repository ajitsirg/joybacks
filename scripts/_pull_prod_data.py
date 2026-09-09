"""
Pull real JoyClub data from production VPS into local SQLite.

Uses a custom serialize on the live API container (includes soft-deleted rows),
then flush + loaddata locally.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import paramiko

HOST = "69.62.82.172"
USER = "root"
KEY = Path.home() / ".ssh" / "sora_vps_key"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FIXTURE = BACKEND / "_prod_data.json"
REMOTE_FIXTURE = "/tmp/joyclub_prod_data.json"
REMOTE_DUMP_PY = "/tmp/_dump_all.py"

# Runs inside the API container so soft-deleted BaseModel rows are included.
DUMP_SCRIPT = r'''
import json
from django.apps import apps
from django.core import serializers

EXCLUDE_APPS = {"contenttypes", "sessions", "admin"}
EXCLUDE_MODELS = {
    ("auth", "permission"),
    ("auth", "group"),
}

objects = []
for model in apps.get_models():
    meta = model._meta
    if meta.app_label in EXCLUDE_APPS:
        continue
    if (meta.app_label, meta.model_name) in EXCLUDE_MODELS:
        continue
    if not meta.managed or meta.proxy:
        continue
    manager = getattr(model, "all_objects", model._default_manager)
    objects.extend(list(manager.all().order_by("pk")))

data = serializers.serialize(
    "json",
    objects,
    indent=2,
    use_natural_foreign_keys=True,
    use_natural_primary_keys=True,
)
path = "/tmp/joyclub_prod_data.json"
with open(path, "w", encoding="utf-8") as fh:
    fh.write(data)
print("wrote", path, "objects", len(objects), "bytes", len(data.encode("utf-8")))
'''


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=str(KEY), timeout=30)

    print("Uploading dump helper…")
    sftp = client.open_sftp()
    with sftp.file(REMOTE_DUMP_PY, "w") as fh:
        fh.write(DUMP_SCRIPT)
    sftp.close()

    dump_cmd = (
        "cd /opt/joyclub && "
        f"docker compose -f docker-compose.prod.yml cp {REMOTE_DUMP_PY} api:/tmp/_dump_all.py && "
        "docker compose -f docker-compose.prod.yml exec -T api "
        "python manage.py shell -c \"exec(open('/tmp/_dump_all.py').read())\""
    )
    print("Dumping production data (including soft-deleted)…")
    _, stdout, stderr = client.exec_command(dump_cmd, timeout=600)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if out.strip():
        print(out[:3000])
    if err.strip():
        print(err[:3000])
        if "Error" in err or "Traceback" in err:
            client.close()
            raise SystemExit("Remote dump failed")

    copy_cmd = (
        "cd /opt/joyclub && docker compose -f docker-compose.prod.yml cp "
        f"api:/tmp/joyclub_prod_data.json {REMOTE_FIXTURE}"
    )
    _, stdout, stderr = client.exec_command(copy_cmd, timeout=120)
    print(stdout.read().decode("utf-8", "replace"))
    print(stderr.read().decode("utf-8", "replace"))

    _, stdout, _ = client.exec_command(
        f"wc -c {REMOTE_FIXTURE}; python3 -c \"import json; d=json.load(open('{REMOTE_FIXTURE}')); print('objects', len(d))\"",
        timeout=120,
    )
    print(stdout.read().decode("utf-8", "replace"))

    print(f"Downloading → {FIXTURE}")
    sftp = client.open_sftp()
    sftp.get(REMOTE_FIXTURE, str(FIXTURE))
    sftp.close()
    client.exec_command(
        f"rm -f {REMOTE_FIXTURE} {REMOTE_DUMP_PY}; "
        "cd /opt/joyclub && docker compose -f docker-compose.prod.yml exec -T api "
        "rm -f /tmp/joyclub_prod_data.json /tmp/_dump_all.py",
        timeout=60,
    )
    client.close()

    size = FIXTURE.stat().st_size
    if size < 100:
        raise SystemExit(f"Fixture too small ({size} bytes) — aborting load")
    print(f"Downloaded {size} bytes")

    py = BACKEND / ".venv" / "Scripts" / "python.exe"
    if not py.exists():
        py = Path(sys.executable)

    db = BACKEND / "db.sqlite3"
    if db.exists():
        bak = BACKEND / "db.sqlite3.pre_prod_pull.bak"
        print(f"Backing up local DB → {bak.name}")
        bak.write_bytes(db.read_bytes())

    print("Flushing local database…")
    subprocess.run(
        [str(py), "manage.py", "flush", "--no-input"],
        cwd=str(BACKEND),
        check=True,
    )
    print("Loading production fixture…")
    subprocess.run(
        [str(py), "manage.py", "loaddata", str(FIXTURE.name)],
        cwd=str(BACKEND),
        check=True,
    )
    print("Migrating…")
    subprocess.run(
        [str(py), "manage.py", "migrate", "--noinput"],
        cwd=str(BACKEND),
        check=True,
    )

    subprocess.run(
        [
            str(py),
            "manage.py",
            "shell",
            "-c",
            (
                "from django.contrib.auth import get_user_model;"
                "from associates.models import Associate;"
                "U=get_user_model();"
                "print('users', U.objects.count());"
                "print('associates', Associate.objects.count());"
                "print('associates_all', Associate.all_objects.count());"
                "print('superusers', list(U.objects.filter(is_superuser=True).values_list('username', flat=True)));"
                "print('sample', list(Associate.objects.order_by('associate_id').values_list('associate_id','status','mobile')[:20]))"
            ),
        ],
        cwd=str(BACKEND),
        check=False,
    )
    print("Done. Local DB now mirrors production data.")


if __name__ == "__main__":
    main()
