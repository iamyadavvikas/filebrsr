"""
Razorpay Subscription Billing for FileBRSR SaaS.
Handles plan creation, subscription management, and webhook processing.
"""
import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _settings():
    return get_settings()

# Razorpay Plan IDs - create these once via Razorpay Dashboard or API
# These map to our internal plan names
PLANS = {
    "starter": {
        "name": "Starter",
        "monthly_amount": 208300,  # ₹2,083/mo (₹25K/yr)
        "yearly_amount": 2500000,   # ₹25,000/yr
        "reports_per_month": 5,
        "features": ["5 reports/month", "Basic gap analysis", "Email support"],
    },
    "professional": {
        "name": "Professional",
        "monthly_amount": 1250000,  # ₹12,500/mo (₹1.5L/yr)
        "yearly_amount": 15000000,  # ₹1,50,000/yr
        "reports_per_month": 50,
        "features": ["50 reports/month", "NIFTY 50 benchmarks", "PDF reports", "Priority support", "Multi-user"],
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_amount": 4166700,  # ₹41,667/mo (₹5L/yr)
        "yearly_amount": 50000000,  # ₹5,00,000/yr
        "reports_per_month": -1,  # unlimited
        "features": ["Unlimited reports", "API access", "Custom integrations", "Dedicated support", "White-label"],
    },
    "pay_per_report": {
        "name": "Pay Per Report",
        "amount": 250000,  # ₹2,500 per report
        "features": ["Single report analysis", "Full gap analysis", "Benchmark comparison"],
    },
}


class CreateSubscriptionRequest(BaseModel):
    plan: str
    billing_period: str = "yearly"  # monthly or yearly
    user_id: str
    org_id: str | None = None


class CreateOrderRequest(BaseModel):
    plan: str = "pay_per_report"
    user_id: str


@router.get("/plans")
async def get_plans():
    """Return all available plans with pricing."""
    return {"plans": PLANS}


@router.post("/create-subscription")
async def create_subscription(req: CreateSubscriptionRequest):
    """Create a Razorpay subscription for recurring billing."""
    if req.plan not in PLANS or req.plan == "pay_per_report":
        raise HTTPException(status_code=400, detail="Invalid plan for subscription")

    plan_data = PLANS[req.plan]
    amount = plan_data["yearly_amount"] if req.billing_period == "yearly" else plan_data["monthly_amount"]
    period = "yearly" if req.billing_period == "yearly" else "monthly"

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Create subscription via Razorpay API
            response = await client.post(
                "https://api.razorpay.com/v1/subscriptions",
                auth=(get_settings().RAZORPAY_KEY_ID, get_settings().RAZORPAY_KEY_SECRET),
                json={
                    "plan_id": f"plan_{req.plan}_{period}",  # Pre-created in Razorpay
                    "total_count": 12 if period == "monthly" else 1,
                    "quantity": 1,
                    "notes": {
                        "user_id": req.user_id,
                        "org_id": req.org_id or "",
                        "plan": req.plan,
                    },
                },
            )

            if response.status_code != 200:
                # Fallback: create a one-time order instead
                order_response = await client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(get_settings().RAZORPAY_KEY_ID, get_settings().RAZORPAY_KEY_SECRET),
                    json={
                        "amount": amount,
                        "currency": "INR",
                        "receipt": f"sub_{req.plan}_{req.user_id[:8]}",
                        "notes": {
                            "user_id": req.user_id,
                            "org_id": req.org_id or "",
                            "plan": req.plan,
                            "billing_period": period,
                        },
                    },
                )
                if order_response.status_code == 200:
                    order_data = order_response.json()
                    return {
                        "type": "order",
                        "order_id": order_data["id"],
                        "amount": amount,
                        "currency": "INR",
                        "key_id": get_settings().RAZORPAY_KEY_ID,
                    }
                raise HTTPException(status_code=500, detail="Failed to create subscription or order")

            sub_data = response.json()
            return {
                "type": "subscription",
                "subscription_id": sub_data["id"],
                "plan": req.plan,
                "amount": amount,
                "currency": "INR",
                "key_id": get_settings().RAZORPAY_KEY_ID,
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Payment gateway error: {str(e)}")


@router.post("/create-order")
async def create_order(req: CreateOrderRequest):
    """Create a one-time Razorpay order for pay-per-report."""
    plan_data = PLANS.get(req.plan)
    if not plan_data:
        raise HTTPException(status_code=400, detail="Invalid plan")

    amount = plan_data.get("amount", plan_data.get("yearly_amount", 0))

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.razorpay.com/v1/orders",
                auth=(get_settings().RAZORPAY_KEY_ID, get_settings().RAZORPAY_KEY_SECRET),
                json={
                    "amount": amount,
                    "currency": "INR",
                    "receipt": f"order_{req.user_id[:8]}",
                    "notes": {"user_id": req.user_id, "plan": req.plan},
                },
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to create order")

            order_data = response.json()
            return {
                "order_id": order_data["id"],
                "amount": amount,
                "currency": "INR",
                "key_id": get_settings().RAZORPAY_KEY_ID,
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Payment gateway error: {str(e)}")


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """Handle Razorpay webhooks for subscription lifecycle events."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # Verify webhook signature
    expected_signature = hmac.HMAC(
        get_settings().RAZORPAY_KEY_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})

    if not entity:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})

    # Handle subscription events
    if event == "subscription.activated":
        await _handle_subscription_activated(entity)
    elif event == "subscription.charged":
        await _handle_subscription_charged(entity)
    elif event == "subscription.cancelled":
        await _handle_subscription_cancelled(entity)
    elif event == "subscription.paused":
        await _handle_subscription_paused(entity)
    elif event == "payment.captured":
        await _handle_payment_captured(entity)

    return {"status": "ok"}


async def _handle_subscription_activated(entity: dict):
    """Activate subscription and grant access."""
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    notes = entity.get("notes", {})
    user_id = notes.get("user_id")
    plan = notes.get("plan", "starter")
    org_id = notes.get("org_id")

    if user_id:
        # Update profile plan
        supabase.table("profiles").update({
            "plan": plan,
            "credits_remaining": PLANS[plan]["reports_per_month"],
        }).eq("id", user_id).execute()

    if org_id:
        supabase.table("organizations").update({
            "subscription_status": "active",
            "plan": plan,
            "subscription_id": entity.get("id"),
        }).eq("id", org_id).execute()


async def _handle_subscription_charged(entity: dict):
    """Reset monthly credits on successful charge."""
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    notes = entity.get("notes", {})
    user_id = notes.get("user_id")
    plan = notes.get("plan", "starter")

    if user_id:
        supabase.table("profiles").update({
            "credits_remaining": PLANS[plan]["reports_per_month"],
        }).eq("id", user_id).execute()


async def _handle_subscription_cancelled(entity: dict):
    """Downgrade to free on cancellation."""
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    notes = entity.get("notes", {})
    user_id = notes.get("user_id")
    org_id = notes.get("org_id")

    if user_id:
        supabase.table("profiles").update({
            "plan": "free",
            "credits_remaining": 3,
        }).eq("id", user_id).execute()

    if org_id:
        supabase.table("organizations").update({
            "subscription_status": "cancelled",
        }).eq("id", org_id).execute()


async def _handle_subscription_paused(entity: dict):
    """Mark subscription as paused."""
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    notes = entity.get("notes", {})
    org_id = notes.get("org_id")
    if org_id:
        supabase.table("organizations").update({
            "subscription_status": "paused",
        }).eq("id", org_id).execute()


async def _handle_payment_captured(entity: dict):
    """Handle one-time payment (pay-per-report)."""
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    notes = entity.get("notes", {})
    user_id = notes.get("user_id")

    if user_id:
        # Add 1 credit for pay-per-report
        profile = supabase.table("profiles").select("credits_remaining").eq("id", user_id).single().execute()
        current_credits = profile.data.get("credits_remaining", 0) if profile.data else 0
        supabase.table("profiles").update({
            "credits_remaining": current_credits + 1,
        }).eq("id", user_id).execute()


@router.post("/verify-payment")
async def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    user_id: str,
    plan: str = "pay_per_report",
):
    """Verify Razorpay payment signature (client-side callback)."""
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.HMAC(
        get_settings().RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(razorpay_signature, expected):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Payment verified — update user credits
    from supabase import create_client
    supabase = create_client(get_settings().SUPABASE_URL, get_settings().SUPABASE_SERVICE_KEY)

    if plan == "pay_per_report":
        profile = supabase.table("profiles").select("credits_remaining").eq("id", user_id).single().execute()
        current = profile.data.get("credits_remaining", 0) if profile.data else 0
        supabase.table("profiles").update({"credits_remaining": current + 1}).eq("id", user_id).execute()
    else:
        supabase.table("profiles").update({
            "plan": plan,
            "credits_remaining": PLANS.get(plan, {}).get("reports_per_month", 5),
        }).eq("id", user_id).execute()

    # Record payment
    supabase.table("payments").insert({
        "user_id": user_id,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
        "amount": PLANS.get(plan, {}).get("amount", PLANS.get(plan, {}).get("yearly_amount", 0)),
        "plan": plan,
        "status": "paid",
    }).execute()

    return {"status": "verified", "plan": plan}
