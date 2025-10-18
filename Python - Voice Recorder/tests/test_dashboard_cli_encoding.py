import subprocess
import sys
import os


def run_cli_with_encoding(args, env=None, encoding=None):
    cmd = [sys.executable, "scripts/dashboard_cli.py"] + args
    myenv = os.environ.copy()
    if env:
        myenv.update(env)
    # Ensure subprocess can import local 'core' package
    myenv["PYTHONPATH"] = os.getcwd()
    # Allow caller to set PYTHONIOENCODING explicitly
    if "PYTHONIOENCODING" not in myenv:
        myenv["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv, text=True, encoding=encoding or myenv.get("PYTHONIOENCODING"))
    return p.returncode, p.stdout, p.stderr


def test_cli_fallback_under_cp1252():
    # Simulate a legacy Windows environment by forcing cp1252 encoding in subprocess
    env = {"VRP_ADMIN_MODE": "1", "PYTHONIOENCODING": "cp1252"}
    rc, out, err = run_cli_with_encoding(["--render", "overview", "--renderer", "text"], env=env, encoding="cp1252")
    assert rc == 0, f"CLI failed under cp1252: stderr={err}"
    # Output should at least contain ASCII labels; ensure no exception and ASCII-only output
    assert out is not None
    assert "Overview" in out or "Recordings Today" in out
    assert all(ord(ch) <= 127 for ch in out), "Fallback did not produce ASCII-only output under cp1252"
