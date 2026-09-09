"""Dump production Postgres and print restore hints for local use."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "69.62.82.172"
USER = "root"
KEY = Path.home() / ".ssh" / "sora_vps_key"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "_prod_dump.sql"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=str(KEY), timeout=30)

    # Discover DB credentials from compose env (without printing password later)
    _, stdout, _ = client.exec_command(
        "cd /opt/joyclub && grep -E '^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD)=' .env.production",
        timeout=30,
    )
    env_lines = stdout.read().decode("utf-8", "replace").strip().splitlines()
    env: dict[str, str] = {}
    for line in env_lines:
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    db = env.get("POSTGRES_DB", "joyclub")
    user = env.get("POSTGRES_USER", "joyclub")
    password = env.get("POSTGRES_PASSWORD", "")
    print(f"Remote DB name={db} user={user}")

    remote_dump = "/tmp/joyclub_prod.dump"
    # Custom format dump (pg_dump -Fc) is portable; also create plain SQL for sqlite fallback
    dump_cmd = (
        f"cd /opt/joyclub && docker compose -f docker-compose.prod.yml exec -T "
        f"-e PGPASSWORD={password!r} db "
        f"pg_dump -U {user} -d {db} --no-owner --no-acl -F p > {remote_dump}"
    )
    print("Creating remote SQL dump…")
    _, stdout, stderr = client.exec_command(dump_cmd, timeout=300)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if out:
        print(out)
    if err and "password" not in err.lower():
        print(err)

    _, stdout, _ = client.exec_command(f"wc -c {remote_dump} && head -c 200 {remote_dump}", timeout=30)
    meta = stdout.read().decode("utf-8", "replace")
    print(meta)

    print(f"Downloading to {OUT}…")
    sftp = client.open_sftp()
    sftp.get(remote_dump, str(OUT))
    sftp.close()
    client.exec_command(f"rm -f {remote_dump}", timeout=30)
    client.close()

    size = OUT.stat().st_size
    print(f"Done. Local dump: {OUT} ({size} bytes)")


if __name__ == "__main__":
    main()
