"""Simple CLI wrapper to list and render dashboards.

Usage (PowerShell):
    $env:VRP_ADMIN_MODE = "1"
    python ./scripts/dashboard_cli.py --list
    python ./scripts/dashboard_cli.py --render overview --renderer text

This script enforces the same access control as the programmatic API.
"""
import argparse
import sys
import os

from core.dashboard.dashboard import Dashboard, render_dashboard
from core.dashboard import access_control


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render or list dashboards")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List available dashboards")
    group.add_argument("--render", metavar="DASHBOARD_ID", help="Render a dashboard by id")
    parser.add_argument("--renderer", choices=["text", "json", "markdown"], default="text", help="Renderer to use")
    parser.add_argument("--utf8", action="store_true", help="Force UTF-8 output (do not replace non-ASCII chars)")
    args = parser.parse_args(argv)

    # Access control check
    try:
        allowed = access_control.check_dashboard_access()
    except Exception:
        allowed = False

    if not allowed:
        print("Dashboard access denied. Enable via VRP_ADMIN_MODE=1 or see docs for config-based enablement.")
        return 2

    if args.list:
        configs = Dashboard.list_available_configs()
        for c in configs:
            print(c)
        return 0

    if args.render:
        try:
            output = render_dashboard(args.render, renderer_type=args.renderer)
            # Decide how to emit output:
            # - If user requested UTF-8 via --utf8, or the environment indicates
            #   UTF-8 is in use (PYTHONIOENCODING or stdout encoding), print
            #   the raw Unicode output.
            # - Otherwise, fall back to an ASCII-safe representation so tests
            #   and legacy terminals don't fail on encoding.
            force_utf8 = args.utf8
            env_pyio = ("" if not hasattr(sys, "getdefaultencoding") else os.environ.get("PYTHONIOENCODING", ""))
            stdout_is_utf8 = (sys.stdout.encoding or "").lower().startswith("utf")
            if force_utf8 or env_pyio.lower().startswith("utf") or stdout_is_utf8:
                # Emit raw Unicode (letting Python/terminal handle encoding)
                print(output)
            else:
                safe_output = output.encode("ascii", errors="replace").decode("ascii")
                print(safe_output)
            return 0
        except FileNotFoundError:
            print(f"Dashboard '{args.render}' not found.")
            return 3
        except Exception as e:
            print(f"Error rendering dashboard: {e}")
            return 4

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
