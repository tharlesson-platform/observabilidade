"""Exercise one real alert rule through the local observability stack."""

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic, sleep
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


EVIDENCE = Path("/tmp/evidence")
PROMETHEUS = "http://prometheus:9090/api/v1"
QUERY = 'probe_success{job="blackbox-http",cluster="alert-lifecycle"}'
degraded = Event()
webhooks = Queue()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def matches(labels):
    return labels.get("alertname") == "BlackboxEndpointDown" and labels.get("cluster") == "alert-lifecycle"


class Fixture(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path != "/health":
            self.reply(404)
            return
        self.reply(503 if degraded.is_set() else 200)

    def do_POST(self):
        if self.path != "/webhook":
            self.reply(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        for alert in payload["alerts"]:
            if matches(alert["labels"]):
                webhooks.put({"received_at": timestamp(), "status": alert["status"], "payload": payload, "alert": alert})
        self.reply(200)

    def log_message(self, _format, *_args):
        pass


def api(path):
    with urlopen(f"{PROMETHEUS}/{path}", timeout=3) as response:
        data = json.load(response)
    if data["status"] != "success":
        raise RuntimeError(f"Prometheus API failed: {path}")
    return data["data"]


def matching_alerts():
    return [alert for alert in api("alerts")["alerts"] if matches(alert["labels"])]


def wait_for(description, check, timeout):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (URLError, TimeoutError):
            pass
        sleep(2)
    raise RuntimeError(f"Timed out waiting for {description}")


def probe_is(expected):
    samples = api("query?" + urlencode({"query": QUERY}))["result"]
    return len(samples) == 1 and float(samples[0]["value"][1]) == expected


def firing_alert():
    return next((alert for alert in matching_alerts() if alert["state"] == "firing"), None)


def notification(status):
    deadline = monotonic() + 60
    while monotonic() < deadline:
        try:
            event = webhooks.get(timeout=max(0, deadline - monotonic()))
        except Empty:
            break
        if event["status"] == status:
            return event
    raise RuntimeError(f"Alertmanager did not deliver a {status} webhook")


def save(name, payload):
    (EVIDENCE / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run():
    wait_for("a healthy probe through the Collector", lambda: probe_is(1), 90)
    failure_at = timestamp()
    degraded.set()
    wait_for("a failing probe through the Collector", lambda: probe_is(0), 45)
    alert = wait_for("Prometheus firing the real rule", firing_alert, 250)
    firing = notification("firing")
    save("firing", {**firing, "fault_injected_at": failure_at, "probe_success": 0, "prometheus_alert": alert})
    print(f"firing webhook received at {firing['received_at']}", flush=True)

    restored_at = timestamp()
    degraded.clear()
    wait_for("the recovered probe", lambda: probe_is(1), 45)
    wait_for("the alert to clear in Prometheus", lambda: not matching_alerts(), 70)
    resolved = notification("resolved")
    if firing["alert"]["fingerprint"] != resolved["alert"]["fingerprint"]:
        raise RuntimeError("Firing and resolved notifications refer to different alerts")
    save("resolved", {**resolved, "target_restored_at": restored_at, "probe_success": 1, "prometheus_alerts": []})
    print(f"resolved webhook received at {resolved['received_at']}", flush=True)


if __name__ == "__main__":
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with ThreadingHTTPServer(("0.0.0.0", 8080), Fixture) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            run()
        finally:
            server.shutdown()
