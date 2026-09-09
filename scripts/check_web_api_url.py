import paramiko
from pathlib import Path

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(str(Path.home() / ".ssh" / "sora_vps_key"))
client.connect("69.62.82.172", username="root", pkey=pkey, look_for_keys=False, allow_agent=False, timeout=30)

cmd = r"""docker exec joyclub-web-1 sh -c "grep -rhoE 'https?://[^\"[:space:]]*api/v1|localhost:8000' /app/.output/public/assets 2>/dev/null | sort | uniq -c | head -30" """
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
print("URLS:", stdout.read().decode())
print("ERR:", stderr.read().decode())

cmd2 = r"""docker exec joyclub-web-1 sh -c "grep -l login /app/.output/public/assets/*.js | head -5; grep -ohE '.{0,40}auth/login.{0,40}' /app/.output/public/assets/*.js | head -10" """
stdin, stdout, stderr = client.exec_command(cmd2, timeout=60)
print("LOGIN:", stdout.read().decode()[:2000])
print("ERR2:", stderr.read().decode()[:500])

# Fetch login page HTML from nginx and find asset, then check that asset
cmd3 = r"""curl -sk https://accounts.dovix.ai/login | head -c 4000; echo; curl -sk https://accounts.dovix.ai/assets/ 2>/dev/null | head -c 500"""
stdin, stdout, stderr = client.exec_command(cmd3, timeout=60)
print("HTML:", stdout.read().decode()[:2500])

client.close()
