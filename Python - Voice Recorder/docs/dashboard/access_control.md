# Access Control for Dashboards

Dashboards are hidden by default. The access control is intentionally conservative for single-user desktop installs.

Enablement options

1. Environment variable (recommended for testing): set `VRP_ADMIN_MODE=1` before running commands that render dashboards.

2. Configuration: set `dashboard.enabled = true` in your configuration file (location depends on your install). When using config-based enablement, prefer a confirmation step in the GUI.

Security considerations

- On shared machines, enabling dashboards may expose operational metrics. Only enable when needed.
- For remote or multi-user deployments, replace or augment this gating mechanism with proper user authentication and role-based access control.
