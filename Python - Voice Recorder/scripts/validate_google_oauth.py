"""Validate Google OAuth client_secrets.json and environment for local testing.

Places to run: repository root. Usage:

  # from the repo root (PowerShell)
  & .\venv\Scripts\python.exe .\scripts\validate_google_oauth.py

This script will:
- Locate `config/client_secrets.json` or use the path set in VRP_CLIENT_SECRETS.
- Parse the JSON and check required fields exist.
- If google libraries are installed, attempt to instantiate the OAuth Flow and print an authorization URL.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def find_client_secrets() -> Path | None:
    env = os.environ.get("VRP_CLIENT_SECRETS")
    if env:
        p = Path(env)
        if p.exists():
            return p
        print(f"VRP_CLIENT_SECRETS is set but file not found: {p}")
        return None
    p = Path.cwd() / "config" / "client_secrets.json"
    if p.exists():
        return p
    return None


def basic_check(cfg: dict) -> list[str]:
    errors = []
    # Google typical client_secrets has either 'installed' or 'web' top-level
    top = None
    if "installed" in cfg:
        top = cfg["installed"]
    elif "web" in cfg:
        top = cfg["web"]
    else:
        errors.append("Top-level key 'installed' or 'web' not found")
        return errors

    for key in ("client_id", "client_secret", "redirect_uris"):
        if key not in top:
            errors.append(f"Missing required key in client config: {key}")

    if not isinstance(top.get("redirect_uris", []), list):
        errors.append("'redirect_uris' should be a list")

    return errors


def try_construct_flow(cfg: dict) -> None:
    try:
        from google_auth_oauthlib.flow import Flow
    except Exception as e:
        print("Google OAuth libraries not installed or not importable:", e)
        print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return

    # Use installed/web top
    top = cfg.get("installed") or cfg.get("web")
    if not top:
        print("No 'installed' or 'web' section found in client_secrets.json; skipping Flow creation")
        return

    try:
        flow = Flow.from_client_config({"installed": top}, scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/drive.file",
        ])
        # Loopback redirect; port will be ephemeral in real flow, but we can set a placeholder
        flow.redirect_uri = "http://127.0.0.1"
        auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
        print("Successfully constructed OAuth Flow. Open the following URL in your browser to test the consent screen:")
        print(auth_url)
    except Exception as e:
        print("Failed to create OAuth Flow from client config:", e)


def main() -> int:
    p = find_client_secrets()
    if not p:
        print("No client_secrets.json found. Place the file at config/client_secrets.json or set VRP_CLIENT_SECRETS to its path.")
        return 2

    print("Found client_secrets.json:", p)
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("Failed to parse JSON:", e)
        return 3

    errs = basic_check(cfg)
    if errs:
        print("Validation errors in client_secrets.json:")
        for e in errs:
            print(" -", e)
        return 4

    print("Basic client_secrets.json checks passed.")
    try_construct_flow(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
