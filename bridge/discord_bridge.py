"""Translate an Alertmanager webhook payload into a Discord message."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import Request, urlopen

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
PORT = int(os.environ.get("PORT", "8080"))


def discord_body(payload: dict) -> bytes:
    lines = []
    for alert in payload.get("alerts", []):
        status = str(alert.get("status", "firing")).upper()
        name = alert.get("labels", {}).get("alertname", "alert")
        summary = alert.get("annotations", {}).get("summary", "")
        lines.append(f"**{status}** `{name}` — {summary}")
    content = "\n".join(lines) or "PipelineWatch alert"
    return json.dumps({"content": content[:1900]}).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}

        if not WEBHOOK:
            self._send(202, b"webhook url empty")
            return

        request = Request(
            WEBHOOK,
            data=discord_body(payload),
            headers={"Content-Type": "application/json", "User-Agent": "PipelineWatch"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                response.read()
        except URLError as exc:
            message = str(exc).encode("utf-8")
            self._send(502, message)
            return
        self._send(200, b"ok")

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args, flush=True)


def main() -> None:
    if WEBHOOK:
        print("discord bridge forwarding to the configured webhook", flush=True)
    else:
        print("DISCORD_WEBHOOK_URL is empty; accepting and dropping alerts", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
