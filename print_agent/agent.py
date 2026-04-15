from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from urllib import error, request


def api_post(base_url: str, path: str, payload: dict, *, key: str) -> tuple[int, dict]:
    req = request.Request(
        url=f"{base_url.rstrip('/')}{path}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Print-Agent-Key": key,
        },
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body) if body else {}
            return response.status, data
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        payload = json.loads(body) if body else {}
        return exc.code, payload


def format_ticket(job: dict) -> str:
    order = job["order"]
    lines = [
        "PIZZERIA ORDER",
        "=" * 32,
        f"Order: #{order['id']}",
        f"Status: {order['status']}",
        f"Attempt: {job['attempt_count']}/{job['max_attempts']}",
        f"Printed at: {datetime.now().isoformat(timespec='seconds')}",
        "-" * 32,
    ]

    for item in order["items"]:
        extras = f" ({item['extras']})" if item.get("extras") else ""
        lines.append(f"x{item['quantity']} Product #{item['product_id']}{extras}")

    lines.extend(
        [
            "-" * 32,
            f"TOTAL: EUR {order['total_price']:.2f}",
            "=" * 32,
        ]
    )
    return "\n".join(lines)


def send_to_printer(ticket: str, *, output_file: str | None) -> None:
    if output_file:
        with open(output_file, "a", encoding="utf-8") as handle:
            handle.write(ticket)
            handle.write("\n\n")
        return

    print(ticket)
    print()


def run_agent(
    *,
    base_url: str,
    key: str,
    agent_id: str,
    interval_seconds: float,
    output_file: str | None,
) -> None:
    while True:
        status, data = api_post(
            base_url,
            "/print-agent/jobs/pull",
            {"agent_id": agent_id},
            key=key,
        )

        if status != 200:
            detail = data.get("detail", "unknown error")
            print(f"[pull] error {status}: {detail}")
            time.sleep(interval_seconds)
            continue

        job = data.get("job")
        if not job:
            time.sleep(interval_seconds)
            continue

        job_id = job["job_id"]
        try:
            ticket = format_ticket(job)
            send_to_printer(ticket, output_file=output_file)
            complete_status, complete_data = api_post(
                base_url,
                f"/print-agent/jobs/{job_id}/complete",
                {"agent_id": agent_id},
                key=key,
            )
            if complete_status != 200:
                raise RuntimeError(complete_data.get("detail", "could not mark print as complete"))
            print(f"[ok] printed order #{job['order']['id']} with job #{job_id}")
        except Exception as exc:  # noqa: BLE001
            fail_status, fail_data = api_post(
                base_url,
                f"/print-agent/jobs/{job_id}/fail",
                {
                    "agent_id": agent_id,
                    "error": str(exc),
                },
                key=key,
            )
            detail = fail_data.get("detail", "no additional details")
            print(f"[fail] job #{job_id} ({fail_status}): {detail}")

        time.sleep(interval_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local print agent for pizzeria orders.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("PRINT_AGENT_API_URL", "http://127.0.0.1:8000"),
        help="Backend API URL",
    )
    parser.add_argument(
        "--agent-id",
        default=os.getenv("PRINT_AGENT_ID", "kitchen-agent-1"),
        help="Unique identifier of this print agent",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("PRINT_AGENT_INTERVAL_SECONDS", "2")),
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--output-file",
        default=os.getenv("PRINT_AGENT_OUTPUT_FILE", ""),
        help="Optional local file path used as print sink",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    key = (os.getenv("PRINT_AGENT_KEY") or "").strip()

    if not key:
        raise SystemExit("PRINT_AGENT_KEY is required")

    output_file = args.output_file.strip() or None
    run_agent(
        base_url=args.api_url,
        key=key,
        agent_id=args.agent_id,
        interval_seconds=max(0.5, args.interval),
        output_file=output_file,
    )


if __name__ == "__main__":
    main()
