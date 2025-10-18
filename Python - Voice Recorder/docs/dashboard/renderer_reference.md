# Renderer Reference

Three renderers exist:

- TextRenderer — CLI-friendly plain text.
- JSONRenderer — machine-readable JSON structure of dashboard contents.
- MarkdownRenderer — human-friendly markdown output suitable for README previews.

Use `renderer` argument in `render_dashboard(name, renderer='text')` to select.

Sample TextRenderer output

```text
Overview - System Health
------------------------
Recordings Today: 12
CPU Usage (24h): ▂▃▅▇▆▅▃▂
Alerts: 0 critical, 1 warning
```

Sample JSONRenderer output

```json
{
  "id": "overview",
  "title": "Overview",
  "widgets": [
    {"type": "metric", "title": "Recordings Today", "value": 12},
    {"type": "chart", "title": "CPU Usage (24h)", "values": [10,20,15]}
  ]
}
```

