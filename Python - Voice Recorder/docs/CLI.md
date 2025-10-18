CLI usage and encoding notes

Overview
--------
The small CLI at `scripts/dashboard_cli.py` provides two main actions:

- `--list` — list available dashboard configs
- `--render <id>` — render a dashboard (choose `--renderer text|json|markdown`)

Encoding and CI recommendations
-------------------------------

The dashboard text renderer uses box-drawing characters and other Unicode. To avoid brittle behavior across different platforms and CI environments we:

- Emit an ASCII-safe fallback by default (replacing non-ASCII chars) so legacy environments (Windows cp1252) won't fail.
- Provide `--utf8` to force raw UTF-8 output when your terminal or CI supports it.

Recommended CI configuration (GitHub Actions)
--------------------------------------------

1. Use UTF-8 as the default in CI so you get full-fidelity Unicode output and don't need to rely on ASCII fallbacks.

Example (GitHub Actions):

env:
  PYTHONIOENCODING: utf-8
  LANG: C.UTF-8

2. Keep a Windows/cp1252 job in the CI matrix to ensure the ASCII fallback continues to work. The repository includes a workflow `./.github/workflows/ci-encoding.yml` which:

- Runs the main test suite in a UTF-8 Linux environment.
- Runs `tests/test_dashboard_cli_encoding.py` on Windows with `PYTHONIOENCODING=cp1252` to validate fallback behavior.

Local testing tips
------------------

On Windows PowerShell, to run tests in a UTF-8 mode for parity with CI:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:LANG = 'C.UTF-8'
python -m pytest tests/test_dashboard_cli.py -q
```

To simulate a legacy environment locally (validates fallback):

```powershell
$env:PYTHONIOENCODING = 'cp1252'
python -m pytest tests/test_dashboard_cli_encoding.py -q
```

If you need the CLI to always emit Unicode, pass `--utf8` explicitly when invoking `--render`.
# Dashboard CLI

A tiny CLI wrapper exists to list and render dashboards from the command line: `scripts/dashboard_cli.py`.

Usage (PowerShell):

```powershell
# Enable dashboards temporarily
$env:VRP_ADMIN_MODE = "1"

# List dashboards
python .\scripts\dashboard_cli.py --list

# Render a dashboard (text)
python .\scripts\dashboard_cli.py --render overview --renderer text

# Render a dashboard as JSON
python .\scripts\dashboard_cli.py --render performance --renderer json
```

Exit codes:

- 0: Success
- 2: Access denied (enable VRP_ADMIN_MODE or update config)
- 3: Dashboard not found
- 4: Error rendering

The CLI enforces the same access control checks as `core.dashboard.access_control`.
