import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARDS = ROOT / "grafana" / "provisioning" / "dashboards" / "json"
REQUIRED = {
    "pipeline-health",
    "data-freshness",
    "failure-rate",
    "logs",
}
DATASOURCES = {"prometheus", "loki"}


def datasources(node, found):
    if isinstance(node, dict):
        source = node.get("datasource")
        if isinstance(source, dict) and source.get("uid"):
            found.add(source["uid"])
        for value in node.values():
            datasources(value, found)
    elif isinstance(node, list):
        for item in node:
            datasources(item, found)


def main() -> int:
    errors = []
    found = set()
    if not DASHBOARDS.is_dir():
        print(f"missing {DASHBOARDS}")
        return 1

    for path in sorted(DASHBOARDS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        for key in ("title", "uid", "panels"):
            if not data.get(key):
                errors.append(f"{path.name}: missing {key}")

        panels = data.get("panels")
        if not isinstance(panels, list) or not panels:
            errors.append(f"{path.name}: panels must be a non-empty list")
            panels = []

        for index, panel in enumerate(panels):
            if not isinstance(panel, dict):
                errors.append(f"{path.name}: panel {index} is not an object")
                continue
            if not panel.get("title") or not panel.get("type"):
                errors.append(f"{path.name}: panel {index} needs title and type")

        uid = data.get("uid")
        found.add(uid)
        used = set()
        datasources(data, used)
        unknown = used - DATASOURCES
        if unknown:
            errors.append(f"{path.name}: unknown datasource uid {sorted(unknown)}")

        if uid == "logs" and not any(panel.get("type") == "logs" for panel in panels):
            errors.append(f"{path.name}: needs a Loki logs panel")
        if uid != "logs" and "prometheus" not in used:
            errors.append(f"{path.name}: needs the Prometheus datasource")

    missing = REQUIRED - found
    if missing:
        errors.append(f"missing dashboard uids: {sorted(missing)}")

    if errors:
        print("\n".join(errors))
        return 1

    print(f"ok {len(found)} dashboards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
