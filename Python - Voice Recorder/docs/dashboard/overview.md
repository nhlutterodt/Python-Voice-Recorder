# Dashboard System — Overview

This page explains how the dashboard system integrates with the Voice Recorder application, the goals of the design, and where to find detailed references for widgets, renderers, and configuration.

Location
--------
The dashboard runtime and implementation live in `core/dashboard/` and built-in dashboard JSON files are in `config/dashboards/`.

Goals
-----
- Provide a dynamic, config-driven dashboard system so new dashboards can be added without code changes.
- Keep the system CLI-first (Text renderer) so it is usable on headless or development machines.
- Gate access to dashboards by default for security on single-user desktop installs.

See the other pages in this folder for access control, widget reference, renderer examples, and the dashboard config schema.
