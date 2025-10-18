# Dashboard Config Schema (informal)

A dashboard JSON is an object with the following top-level fields:

- `id` (string) — unique id or filename base for the dashboard.
- `title` (string) — title shown in renderers.
- `description` (string, optional) — short description.
- `widgets` (array) — ordered list of widget definitions; each widget is an object with `type`, `title`, and `config`.

Example:

```json
{
  "id": "overview",
  "title": "Overview",
  "widgets": [
    {"type": "metric", "title": "Recordings Today", "config": {"metric": "recordings.count", "aggregation": "sum"}}
  ]
}
```

Place custom dashboard JSON files under `config/dashboards/`. The dashboard loader will pick them up by filename.
