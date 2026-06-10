from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from urllib import error, request

DEFAULT_TICKET_WIDTH = 42


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
    width = _ticket_width()
    created_at = _format_datetime(order.get("created_at"))
    payment_method = str(order.get("payment_method", "")).upper() or "PAYMENT"
    title = os.getenv("PRINT_AGENT_TICKET_TITLE", "PIZZERIA")
    display_order_number = order.get("daily_order_number", order["id"])

    lines = [
        "=" * width,
        title[:width].center(width),
        "=" * width,
        _two_column(f"ORDER #{display_order_number}", payment_method, width),
        created_at,
        "",
        "CUSTOMER",
        str(order.get("customer_name") or "").strip(),
        str(order.get("customer_phone") or "").strip(),
    ]

    customer_email = str(order.get("customer_email") or "").strip()
    if customer_email:
        lines.append(customer_email)

    lines.extend(
        [
            "",
            "DELIVERY",
            str(order.get("delivery_address") or "").strip(),
            str(order.get("delivery_city") or "").strip(),
            str(order.get("delivery_postal_code") or "").strip(),
        ]
    )

    delivery_notes = str(order.get("delivery_notes") or "").strip()
    if delivery_notes:
        lines.extend(["", "NOTES", *_wrap_lines(delivery_notes, width)])

    lines.extend(["", "-" * width, "ITEMS"])

    for item in order["items"]:
        extras = f" ({item['extras']})" if item.get("extras") else ""
        product_name = item.get("product_name") or f"Product #{item['product_id']}"
        lines.extend(_wrap_lines(f"{item['quantity']}x {product_name}{extras}", width))

    lines.extend(
        [
            "-" * width,
            _money_line("Subtotal", order.get("subtotal", 0), width),
            _money_line("Delivery", order.get("delivery_fee", 0), width),
            _money_line("TOTAL", order["total_price"], width),
            "=" * width,
            f"Internal order ID: {order['id']}",
            f"Attempt: {job['attempt_count']}/{job['max_attempts']}",
            f"Printed: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def _format_datetime(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value[:16]


def _ticket_width() -> int:
    try:
        return max(32, int(os.getenv("PRINT_AGENT_TICKET_WIDTH", str(DEFAULT_TICKET_WIDTH))))
    except ValueError:
        return DEFAULT_TICKET_WIDTH


def _two_column(left: str, right: str, width: int) -> str:
    available = width - len(right)
    if available <= len(left):
        return left[:width]
    return f"{left}{right.rjust(available)}"


def _money_line(label: str, amount: float | int | str, width: int) -> str:
    try:
        value = f"GBP {float(amount):.2f}"
    except (TypeError, ValueError):
        value = str(amount)
    return _two_column(f"{label}:", value, width)


def _wrap_lines(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


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
