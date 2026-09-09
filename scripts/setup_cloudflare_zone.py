#!/usr/bin/env python3
"""Create / update the joyclubs.in Cloudflare zone (orange-cloud proxy).

Requires a Cloudflare API token in CF_API_TOKEN with:
  Zone.Zone Edit, Zone.DNS Edit, Zone.SSL and Certificates Edit,
  Zone.Zone Settings Edit

Create a token: https://dash.cloudflare.com/profile/api-tokens
  Use the "Edit zone DNS" template, then add Zone Settings + SSL permissions
  (or allow All zones if the site is not in the account yet).

Does not change GoDaddy nameservers — print those after the zone exists.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

DOMAIN = os.environ.get("JOYCLUB_DOMAIN", "joyclubs.in")
ORIGIN = os.environ.get("JOYCLUB_ORIGIN_IP", "69.62.82.172")
API = "https://api.cloudflare.com/client/v4"


def cf(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        err = exc.read().decode()
        raise SystemExit(f"Cloudflare API {method} {path} failed ({exc.code}): {err}") from exc
    if not payload.get("success"):
        raise SystemExit(f"Cloudflare API {method} {path} error: {payload}")
    return payload


def upsert_dns(token: str, zone_id: str, name: str, rtype: str, content: str) -> None:
    existing = cf("GET", f"/zones/{zone_id}/dns_records?name={name}&type={rtype}", token)
    records = existing.get("result") or []
    body = {
        "type": rtype,
        "name": name,
        "content": content,
        "ttl": 1,
        "proxied": True,
    }
    if records:
        rid = records[0]["id"]
        cf("PUT", f"/zones/{zone_id}/dns_records/{rid}", token, body)
        print(f"Updated {rtype} {name} → {content} (proxied)")
        return
    cf("POST", f"/zones/{zone_id}/dns_records", token, body)
    print(f"Created {rtype} {name} → {content} (proxied)")


def main() -> int:
    token = os.environ.get("CF_API_TOKEN", "").strip()
    if not token:
        print(
            "Missing CF_API_TOKEN.\n"
            "Create a token at https://dash.cloudflare.com/profile/api-tokens\n"
            "then run: CF_API_TOKEN=... python3 scripts/setup_cloudflare_zone.py",
            file=sys.stderr,
        )
        return 2

    zones = cf("GET", f"/zones?name={DOMAIN}", token).get("result") or []
    if zones:
        zone = zones[0]
        print(f"Zone already exists: {zone['id']} status={zone.get('status')}")
    else:
        created = cf("POST", "/zones", token, {"name": DOMAIN, "jump_start": False})
        zone = created["result"]
        print(f"Created zone {zone['id']}")

    zone_id = zone["id"]
    upsert_dns(token, zone_id, DOMAIN, "A", ORIGIN)
    upsert_dns(token, zone_id, f"www.{DOMAIN}", "A", ORIGIN)

    cf("PATCH", f"/zones/{zone_id}/settings/ssl", token, {"value": "full"})
    print("SSL mode: full (origin already has a Let's Encrypt cert)")
    cf(
        "PATCH",
        f"/zones/{zone_id}/settings/always_use_https",
        token,
        {"value": "on"},
    )
    print("Always Use HTTPS: on")
    cf(
        "PATCH",
        f"/zones/{zone_id}/settings/automatic_https_rewrites",
        token,
        {"value": "on"},
    )
    cf(
        "PATCH",
        f"/zones/{zone_id}/settings/min_tls_version",
        token,
        {"value": "1.2"},
    )

    zone = cf("GET", f"/zones/{zone_id}", token)["result"]
    nameservers = zone.get("name_servers") or []
    print("\nZone status:", zone.get("status"))
    print("Set these nameservers at GoDaddy (joyclubs.in → DNS → Nameservers):")
    for ns in nameservers:
        print(f"  {ns}")
    print(
        "\nLeave the VPS IP as-is. After nameservers propagate, visitors hit "
        "Cloudflare anycast IPs instead of 69.62.82.172."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
