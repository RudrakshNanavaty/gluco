"""Provider-neutral measured minute summaries for the existing HTTP ingestion API.

No raw-sample aggregation or provider API authentication is inferred here.
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import NAMESPACE_URL, uuid5


def event_for_measurement(record):
    """Normalize an explicitly measured, UTC-aligned minute with stable identity."""
    sensor = record["sensor_id"]
    if not isinstance(sensor, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", sensor):
        raise ValueError("Pseudonymous sensor ID required")
    observed = datetime.fromisoformat(record["observed_at"])
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("Timezone required")
    observed = observed.astimezone(timezone.utc)
    if observed.second or observed.microsecond:
        raise ValueError("Provide already aggregated, minute-aligned observations")
    if record.get("provenance") != "measured":
        raise ValueError("Measured provenance required; replay uses a separate adapter")
    units = record.get("units")
    if units != {"motion": "g", "temperature": "degC", "heart_rate": "bpm"}:
        raise ValueError("Explicit normalized units required")
    values = {}
    for name in ("enmo_mean_g", "temperature_mean_c", "hr_mean_bpm"):
        value = record.get(name)
        if value is None and name == "hr_mean_bpm":
            values[name] = None
            continue
        if isinstance(value, bool) or value is None:
            raise ValueError("Required numeric measurement missing")
        value = float(value)
        if not math.isfinite(value) or (name == "enmo_mean_g" and value < 0):
            raise ValueError("Invalid measurement")
        if name == "hr_mean_bpm" and value <= 0:
            raise ValueError("Invalid heart rate")
        values[name] = value
    identity = f"gluco-measured/{sensor}/{observed.isoformat()}"
    return {
        "event_id": str(uuid5(NAMESPACE_URL, identity)),
        "sensor_id": f"device:{sensor}",
        "observed_at": observed.isoformat(),
        "schema_version": 1,
        "measurements": {
            "contract": "wearable_minute_summary_v1",
            **values,
            "provenance": "measured",
            "units": units,
        },
    }


def send(url, key, event):
    parsed = urlparse(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError("HTTPS required except for loopback development")
    if parsed.username or parsed.password or not key:
        raise ValueError("Use the API key environment variable")
    request = Request(
        url,
        data=json.dumps(event, allow_nan=False).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": key},
    )

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    handlers = [NoRedirect()]
    if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        handlers.append(ProxyHandler({}))
    with build_opener(*handlers).open(request, timeout=30) as response:
        result = json.loads(response.read(10000))
    if (
        not isinstance(result, dict)
        or any(
            type(result.get(k)) is not int or result[k] < 0
            for k in ("accepted", "inserted", "duplicates")
        )
        or result["accepted"] != 1
        or result["inserted"] + result["duplicates"] != 1
    ):
        raise ValueError("Invalid ingestion receipt")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument(
        "--send", action="store_true", help="Send up to 1000 stdin JSONL minutes"
    )
    args = parser.parse_args()
    key = os.environ.get("SENSOR_INGEST_API_KEY", "")
    accepted = inserted = duplicates = count = 0
    try:
        # Validate the entire bounded input before sending any row.
        events = []
        while True:
            line = sys.stdin.readline(10001)
            if not line:
                break
            if len(events) >= 1000 or len(line) > 10000:
                raise ValueError("Input budget exceeded")
            events.append(event_for_measurement(json.loads(line)))
        if not events:
            raise ValueError("No input")
        for event in events:
            count += 1
            if args.send:
                result = send(args.url, key, event)
                accepted += result["accepted"]
                inserted += result["inserted"]
                duplicates += result["duplicates"]
    except Exception:  # noqa: BLE001 - never expose API keys, source rows or remote bodies
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "device_adapter_failed",
                    "processed": count,
                    "partial_delivery_possible": args.send,
                }
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": "pass",
                "sent": args.send,
                "validated": len(events),
                "accepted": accepted,
                "inserted": inserted,
                "duplicates": duplicates,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
