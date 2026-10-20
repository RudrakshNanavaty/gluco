"""Ordered finite DAG, failure notification settings and measured input adapter."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from managed_workflow import build_job
from replay_config import ReplayConfig
from wearable_adapter import event_for_measurement, send


def config():
    return ReplayConfig(
        "managed-test",
        "2026-10-04T07:00:00-04:00",
        "2026-10-04T07:00:00-04:00",
        "2026-10-04T07:00:00-04:00",
        "2026-10-04T07:15:00-04:00",
        "a" * 32,
    )


def test_dag_is_ordered_bounded_and_never_unpauses_schedule():
    job = build_job(
        config(),
        "db.example.org",
        5432,
        "/Workspace/Shared/test",
        ["operator@example.org"],
        11154,
        "0 0 * * * ?",
    )
    assert job["max_concurrent_runs"] == 1 and job["timeout_seconds"] == 2400
    assert job["schedule"]["pause_status"] == "PAUSED"
    assert job["email_notifications"]["on_failure"] == ["operator@example.org"]
    assert [t["task_key"] for t in job["tasks"]] == [
        "prepare",
        "emit",
        "bronze",
        "publish",
        "verify_publication",
    ]
    for previous, task in zip(job["tasks"], job["tasks"][1:]):
        assert task["depends_on"] == [{"task_key": previous["task_key"]}]
    assert (
        job["tasks"][-1]["notebook_task"]["base_parameters"]["expected_windows"]
        == "11154"
    )


@pytest.mark.parametrize("emails,count", [([], 1), (["invalid"], 1), (["a@b.org"], 0)])
def test_missing_operational_contract_rejected(emails, count):
    with pytest.raises(ValueError):
        build_job(
            config(), "db.example.org", 5432, "/Workspace/Shared/test", emails, count
        )


def minute():
    return {
        "sensor_id": "wearable-1",
        "observed_at": "2026-10-20T12:00:00Z",
        "provenance": "measured",
        "enmo_mean_g": 0.1,
        "temperature_mean_c": 32.1,
        "units": {"motion": "g", "temperature": "degC", "heart_rate": "bpm"},
    }


def test_adapter_preserves_missing_hr_and_stable_identity():
    a = event_for_measurement(minute())
    b = event_for_measurement({**minute(), "observed_at": "2026-10-20T08:00:00-04:00"})
    assert a == b
    assert a["measurements"]["hr_mean_bpm"] is None
    assert "demo" not in a["measurements"]
    assert a["sensor_id"].startswith("device:")


@pytest.mark.parametrize(
    "changes",
    [
        {"provenance": "synthetic"},
        {"units": {"temperature": "F"}},
        {"observed_at": "2026-10-20T12:00:01Z"},
        {"observed_at": "2026-10-20T12:00:00"},
        {"enmo_mean_g": -1},
        {"temperature_mean_c": float("nan")},
        {"hr_mean_bpm": 0},
    ],
)
def test_invalid_or_ambiguous_measurements_fail(changes):
    with pytest.raises(ValueError):
        event_for_measurement({**minute(), **changes})


def test_remote_plaintext_is_rejected_before_network():
    with pytest.raises(ValueError, match="HTTPS"):
        send(
            "http://example.org/v1/events", "test-key", event_for_measurement(minute())
        )


def test_http_adapter_transports_auth_and_stable_retry_event():
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    seen = set()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            assert self.headers["X-API-Key"] == "local-test-key"
            event = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            duplicate = event["event_id"] in seen
            seen.add(event["event_id"])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "accepted": 1,
                        "inserted": int(not duplicate),
                        "duplicates": int(duplicate),
                    }
                ).encode()
            )

    class LoopbackServer(HTTPServer):
        def server_bind(self):
            # No reverse-DNS lookup is needed for a loopback-only test server.
            from socketserver import TCPServer

            TCPServer.server_bind(self)
            self.server_name = "localhost"
            self.server_port = self.server_address[1]

    server = LoopbackServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/events"
        event = event_for_measurement(minute())
        assert send(url, "local-test-key", event)["inserted"] == 1
        assert send(url, "local-test-key", event)["duplicates"] == 1
        assert len(seen) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
