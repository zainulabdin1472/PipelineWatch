"""Render alertmanager.yml from the template and the process environment."""

from __future__ import annotations

import os
import sys
from pathlib import Path

TEMPLATE = Path(os.environ.get("TEMPLATE_PATH", "/template/alertmanager.yml.template"))
OUTPUT = Path(os.environ.get("OUTPUT_PATH", "/out/alertmanager.yml"))


def yaml_double(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def receiver_block(name: str, url: str) -> str:
    if name == "empty":
        return "  - name: empty\n"
    if name == "discord":
        return (
            "  - name: discord\n"
            "    webhook_configs:\n"
            "      - url: http://discord-bridge:8080/alert\n"
            "        send_resolved: true\n"
        )
    return (
        "  - name: slack\n"
        "    slack_configs:\n"
        f"      - api_url: {yaml_double(url)}\n"
        "        send_resolved: true\n"
        "        title: '{{ .Status | toUpper }}: {{ .CommonLabels.alertname }}'\n"
        '        text: \'{{ range .Alerts }}{{ .Annotations.summary }}{{"\\n"}}{{ end }}\'\n'
    )


def main() -> None:
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    requested = os.environ.get("ALERT_RECEIVER", "slack").strip().lower() or "slack"
    if requested not in {"slack", "discord"}:
        print(f"unknown ALERT_RECEIVER={requested!r}; use slack or discord", file=sys.stderr)
        raise SystemExit(2)

    name = requested if url else "empty"
    if not url:
        print("ALERT_WEBHOOK_URL is empty; alerts stay in the Alertmanager UI")
    elif name == "discord":
        print("routing alerts to the Discord bridge")
    else:
        print("routing alerts to Slack")

    rendered = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__RECEIVER_NAME__", name)
        .replace("__RECEIVER_BLOCK__", receiver_block(name, url).rstrip())
    )
    if "__" in rendered:
        print("template placeholders left in output", file=sys.stderr)
        raise SystemExit(1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not rendered.endswith("\n"):
        rendered += "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
