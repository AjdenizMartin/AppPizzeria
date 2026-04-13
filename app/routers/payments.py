import stripe
from fastapi import APIRouter, HTTPException

from app.schemas.payment import CheckoutRequest, CheckoutResponse
from app.services.stripe_service import create_checkout

router = APIRouter(tags=["payments"])


@router.post("/create-checkout-session", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest):
    items = payload.items

    if not items:
        raise HTTPException(status_code=400, detail="No items provided")

    try:
        url = create_checkout(items)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except stripe.error.AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Stripe rejected the configured secret key. Update STRIPE_KEY in your .env file.",
        ) from exc
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Stripe checkout is temporarily unavailable. Please try again.",
        ) from exc

    return {"url": url}
