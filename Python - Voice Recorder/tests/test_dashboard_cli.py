import subprocess
import sys
import os


def run_cli(args, env=None):
    cmd = [sys.executable, "scripts/dashboard_cli.py"] + args
    myenv = os.environ.copy()
    if env:
        myenv.update(env)
    # Ensure subprocess can import local 'core' package
    myenv["PYTHONPATH"] = os.getcwd()
    # Ensure subprocess emits/decodes utf-8 by default in CI/test environments
    myenv["PYTHONIOENCODING"] = myenv.get("PYTHONIOENCODING", "utf-8")
    # Decode subprocess output as UTF-8 in the parent to avoid decoding errors
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


def test_cli_list_and_render_overview():
    # Ensure dashboards are enabled via env
    rc, out, _ = run_cli(["--list"], env={"VRP_ADMIN_MODE": "1"})
    assert rc == 0
    # Expect at least the built-in 'overview' dashboard to be listed
    assert "overview" in out

    # Render the overview dashboard as text (default behavior)
    rc2, out2, _ = run_cli(["--render", "overview", "--renderer", "text"], env={"VRP_ADMIN_MODE": "1"})
    assert rc2 == 0
    assert "Overview" in out2 or "Recordings Today" in out2

    # Render with explicit UTF-8 emission and ensure Unicode characters are present
    rc3, out3, _ = run_cli(["--render", "overview", "--renderer", "text", "--utf8"], env={"VRP_ADMIN_MODE": "1"})
    assert rc3 == 0
    # Expect at least one non-ascii character (e.g., box drawing or em dash) in full UTF-8 output
    assert any(ord(ch) > 127 for ch in out3)
