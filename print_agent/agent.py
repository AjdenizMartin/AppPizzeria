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
    created_dt = _parse_datetime(order.get("created_at"))
    created_at = _format_datetime(created_dt)
    created_time = created_dt.strftime("%H:%M")
    created_date = created_dt.strftime("%d/%m/%Y")
    payment_method = str(order.get("payment_method", "")).upper() or "PAYMENT"
    title = os.getenv("PRINT_AGENT_TICKET_TITLE", "Pizzeria Il Basilico")
    display_order_number = order.get("daily_order_number", order["id"])
    order_code = _order_code(order, display_order_number)
    order_type = "DELIVERY" if order_code.startswith("D") else "TAKEAWAY"
    payment_status = "UNPAID" if payment_method == "CASH" else "PAID ONLINE"
    item_count = sum(int(item.get("quantity", 0)) for item in order.get("items", []))

    lines = [
        "",
        title[:width].center(width),
        _restaurant_phone(width),
        *_restaurant_address(width),
        "-" * width,
        f"==={order_type} ORDER===".center(width),
        _two_column(order_code, payment_method, width),
        created_at,
        "",
        "CUSTOMER".center(width),
        _safe_text(order.get("customer_name")),
        _safe_text(order.get("customer_phone")),
    ]

    customer_email = str(order.get("customer_email") or "").strip()
    if customer_email:
        lines.append(customer_email)

    lines.extend(["", "ADDRESS".center(width)])
    address = [
        _safe_text(order.get("delivery_address")),
        _safe_text(order.get("delivery_city")),
        _safe_text(order.get("delivery_postal_code")),
    ]
    lines.extend(line for line in address if line)

    delivery_notes = str(order.get("delivery_notes") or "").strip()
    if delivery_notes:
        lines.extend(["", "NOTES".center(width), *_wrap_lines(delivery_notes, width)])

    lines.extend(["", "-" * width, "ITEMS".center(width)])

    for item in order["items"]:
        product_name = item.get("product_name") or f"Product #{item['product_id']}"
        lines.extend(_item_lines(item, product_name, width))

    lines.extend(
        [
            f"Item {item_count}",
            "-" * width,
            _money_line("Subtotal", order.get("subtotal", 0), width),
            _money_line("Delivery Charge", order.get("delivery_fee", 0), width),
            _total_line(order["total_price"], width),
            "-" * width,
            _two_column("In:", "Out:", width),
            _two_column(created_time, "ASAP", width),
            "",
            order_code,
            created_date,
            f"Ref:{order['id']}",
            f"System: {os.getenv('PRINT_AGENT_SYSTEM_NAME', 'Pizzeria App')}",
            payment_status,
            _money_line("Due", order["total_price"] if payment_status == "UNPAID" else 0, width),
            "-" * width,
            f"Attempt: {job['attempt_count']}/{job['max_attempts']}",
            f"Printed: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now()


def _format_datetime(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _restaurant_phone(width: int) -> str | None:
    phone = os.getenv("PRINT_AGENT_TICKET_PHONE", "014832993").strip()
    if not phone:
        return None
    return f"(T): {phone}"[:width].center(width)


def _restaurant_address(width: int) -> list[str]:
    raw = os.getenv(
        "PRINT_AGENT_TICKET_ADDRESS",
        "5 CENTRAL TERRACE|NORTHGATE|STREET ATHLONE|CO. WESTMEATH|N37 P2R8",
    )
    return [line.strip()[:width].center(width) for line in raw.split("|") if line.strip()]


def _order_code(order: dict, daily_order_number: int) -> str:
    prefix = "D" if float(order.get("delivery_fee") or 0) > 0 else "T"
    return f"{prefix}{int(daily_order_number):04d}"


def _ticket_width() -> int:
    try:
        return max(32, int(os.getenv("PRINT_AGENT_TICKET_WIDTH", str(DEFAULT_TICKET_WIDTH))))
    except ValueError:
        return DEFAULT_TICKET_WIDTH


def _two_column(left: str, right: str, width: int) -> str:
    if len(left) + len(right) >= width:
        return f"{left[: max(0, width - len(right) - 1)]} {right}"[:width]
    return f"{left}{right.rjust(width - len(left))}"


def _money_line(label: str, amount: float | int | str, width: int) -> str:
    try:
        value = f"€{float(amount):.2f}"
    except (TypeError, ValueError):
        value = str(amount)
    return _two_column(f"{label}:", value, width)


def _total_line(amount: float | int | str, width: int) -> str:
    try:
        value = f"€{float(amount):.2f}"
    except (TypeError, ValueError):
        value = str(amount)
    return _two_column("TOTAL:", value, width)


def _item_lines(item: dict, product_name: str, width: int) -> list[str]:
    quantity = int(item.get("quantity", 1))
    line_total = float(item.get("price", 0)) * quantity
    item_title = f"{quantity} x {product_name.upper()}"
    lines = [_two_column(item_title, f"{line_total:.2f}", width)]
    extras = _safe_text(item.get("extras"))
    if extras:
        lines.extend(f"  {line}" for line in _wrap_lines(extras, width - 2))
    return lines


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
