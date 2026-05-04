import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.observability import log_business_event
from app.schemas.payment import CheckoutRequest, CheckoutResponse
from app.services.order_service import mark_order_paid_after_checkout
from app.services.stripe_service import construct_webhook_event, create_checkout

router = APIRouter(tags=["payments"])


@router.post("/create-checkout-session", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest, request: Request):
    items = payload.items

    if not items:
        raise HTTPException(status_code=400, detail="No items provided")

    try:
        url = create_checkout(items, order_id=payload.order_id)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except stripe.error.AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Stripe rejected the configured secret key. "
                "Update STRIPE_KEY in your .env file."
            ),
        ) from exc
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Stripe checkout is temporarily unavailable. Please try again.",
        ) from exc

    log_business_event(
        event="payment_checkout_session_created",
        request=request,
        order_id=payload.order_id,
        payment_method="card",
    )

    return {"url": url}


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    payload = await request.body()

    try:
        event = construct_webhook_event(payload, stripe_signature)
    except ValueError as exc:
        detail = str(exc)
        if "STRIPE_WEBHOOK_SECRET" in detail or "Insecure configuration" in detail:
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc

    if event.get("type") != "checkout.session.completed":
        return {"ok": True, "ignored": True}

    session_object = event.get("data", {}).get("object", {})
    metadata = session_object.get("metadata", {}) or {}
    order_id_raw = metadata.get("order_id")

    if not order_id_raw:
        return {"ok": True, "ignored": True}

    try:
        order_id = int(order_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid order_id in metadata") from None

    try:
        mark_order_paid_after_checkout(db, order_id=order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_business_event(
        event="payment_webhook_completed",
        request=request,
        order_id=order_id,
        payment_method="card",
        status="accepted",
    )

    return {"ok": True}
