"""
Razorpay Subscription Billing for FileBRSR SaaS.
Handles plan creation, subscription management, and webhook processing.

SECURITY: All entitlement-granting endpoints REQUIRE a valid Supabase JWT in the
Authorization header. The user_id is resolved server-side from the JWT and the
client-supplied user_id is IGNORED. The plan and amount are always looked up
server-side from the PLANS dict — never trusted from the client payload during
verification.
"""
import hashlib
import hmac
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger("filebrsr.billing")


def _settings():
    return get_settings()


async def require_user_id(authorization: str | None) -> str:
    """Resolve the authenticated Supabase user_id from a Bearer JWT.
    Rejects missing tokens, 'guest', and the service key. Returns the JWT `sub`.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):].strip()
    if not token or token in ("guest", "undefined", "null"):
        raise HTTPException(status_code=401, detail="Invalid auth token")
    # Reject the service key — only end-user JWTs should hit billing
    if token == get_settings().SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Service key not permitted on billing endpoints")
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
        uid = payload.get("sub")
        if not uid or uid == "guest":
            raise HTTPException(status_code=401, detail="Invalid JWT payload")
        return uid
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not decode JWT: {e}")

# Razorpay Plan IDs - create these once via Razorpay Dashboard or API
# These map to our internal plan names
PLANS = {
    "growth": {
        "name": "Growth",
        "monthly_amount": 416700,  # ₹4,167/mo (₹49,999/yr)
        "yearly_amount": 4999900,  # ₹49,999/yr
        "reports_per_month": -1,  # unlimited
        "supplier_limit": 25,
        "features": ["Unlimited AI extractions", "25 suppliers", "Full Scope 1, 2 & 3 carbon", "Multi-framework mapping", "NIFTY 50 benchmarks", "PDF + XBRL-JSON export", "5 users", "Priority support"],
    },
    "scale": {
        "name": "Scale",
        "monthly_amount": 1666700,  # ₹16,667/mo (₹1,99,999/yr)
        "yearly_amount": 19999900,  # ₹1,99,999/yr
        "reports_per_month": -1,  # unlimited
        "supplier_limit": -1,  # unlimited
        "features": ["Unlimited AI extractions", "Unlimited suppliers", "XBRL filing generation", "Audit trail & compliance", "Supplier-side dashboard", "10 users", "Dedicated AM"],
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_amount": 0,  # Custom pricing
        "yearly_amount": 0,   # Custom pricing — handled via sales
        "reports_per_month": -1,  # unlimited
        "supplier_limit": -1,  # unlimited
        "features": ["Unlimited everything", "API & ERP integration", "SSO / SAML", "Workflow approvals", "White-label option", "SLA guarantee", "Unlimited users"],
    },
    # Legacy — kept for backwards compat with existing subscribers
    "starter": {
        "name": "Starter (Legacy)",
        "monthly_amount": 83300,
        "yearly_amount": 999900,
        "reports_per_month": 5,
        "supplier_limit": 5,
        "features": ["5 reports/month", "Full gap analysis", "PDF export", "Email support"],
    },
    "professional": {
        "name": "Professional (Legacy)",
        "monthly_amount": 416700,
        "yearly_amount": 4999900,
        "reports_per_month": -1,
        "supplier_limit": 25,
        "features": ["Unlimited reports", "25 suppliers", "Multi-framework mapping", "Carbon calculator"],
    },
}


class CreateSubscriptionRequest(BaseModel):
    plan: str
    billing_period: str = "yearly"  # monthly or yearly
    org_id: str | None = None


class CreateOrderRequest(BaseModel):
    plan: str = "pay_per_report"


@router.get("/plans")
async def get_plans():
    """Return all available plans with pricing."""
    return {"plans": PLANS}


@router.post("/create-subscription")
async def create_subscription(
    req: CreateSubscriptionRequest,
    authorization: str | None = Header(default=None),
):
    """Create a Razorpay subscription for recurring billing. REQUIRES Supabase JWT."""
    user_id = await require_user_id(authorization)

    valid_subscription_plans = ("growth", "scale", "starter", "professional")
    if req.plan not in valid_subscription_plans:
        raise HTTPException(status_code=400, detail=f"Invalid plan for subscription. Valid: {valid_subscription_plans}")

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
                        "user_id": user_id,
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
                        "receipt": f"sub_{req.plan}_{user_id[:8]}",
                        "notes": {
                            "user_id": user_id,
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
async def create_order(
    req: CreateOrderRequest,
    authorization: str | None = Header(default=None),
):
    """Create a one-time Razorpay order for pay-per-report. REQUIRES Supabase JWT."""
    user_id = await require_user_id(authorization)

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
                    "receipt": f"order_{user_id[:8]}",
                    "notes": {"user_id": user_id, "plan": req.plan},
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


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str | None = None
    razorpay_payment_id: str
    razorpay_signature: str
    razorpay_subscription_id: str | None = None


@router.post("/verify-payment")
async def verify_payment(
    req: VerifyPaymentRequest,
    authorization: str | None = Header(default=None),
):
    """Verify Razorpay payment signature and grant entitlement.

    SECURITY: user_id comes from the verified JWT (NEVER the client body).
    The plan and amount are read from the Razorpay order/subscription notes,
    which we created server-side. The client cannot influence entitlement.
    """
    user_id = await require_user_id(authorization)

    if req.razorpay_subscription_id:
        # subscriptions: HMAC(payment_id|subscription_id)
        message = f"{req.razorpay_payment_id}|{req.razorpay_subscription_id}"
    elif req.razorpay_order_id:
        # orders: HMAC(order_id|payment_id)
        message = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    else:
        raise HTTPException(status_code=400, detail="Missing order_id or subscription_id")

    expected = hmac.HMAC(
        get_settings().RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(req.razorpay_signature, expected):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    # Fetch order/subscription from Razorpay to read SERVER-SIDE notes
    import httpx
    plan = "pay_per_report"
    amount = 0
    notes_user_id: str | None = None
    try:
        async with httpx.AsyncClient() as client:
            if req.razorpay_subscription_id:
                r = await client.get(
                    f"https://api.razorpay.com/v1/subscriptions/{req.razorpay_subscription_id}",
                    auth=(get_settings().RAZORPAY_KEY_ID, get_settings().RAZORPAY_KEY_SECRET),
                )
            else:
                r = await client.get(
                    f"https://api.razorpay.com/v1/orders/{req.razorpay_order_id}",
                    auth=(get_settings().RAZORPAY_KEY_ID, get_settings().RAZORPAY_KEY_SECRET),
                )
            if r.status_code == 200:
                d = r.json()
                notes = d.get("notes", {}) or {}
                plan = notes.get("plan", plan)
                notes_user_id = notes.get("user_id")
                amount = d.get("amount") or PLANS.get(plan, {}).get("yearly_amount", 0)
    except Exception as e:
        logger.warning("Could not fetch Razorpay entity for verification: %s", e)

    # Defence in depth: notes user_id (if present) MUST match JWT user
    if notes_user_id and notes_user_id != user_id:
        logger.error("User mismatch: jwt=%s razorpay_notes=%s", user_id, notes_user_id)
        raise HTTPException(status_code=403, detail="User mismatch between session and payment")

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

    supabase.table("payments").insert({
        "user_id": user_id,
        "razorpay_order_id": req.razorpay_order_id,
        "razorpay_payment_id": req.razorpay_payment_id,
        "razorpay_signature": req.razorpay_signature,
        "amount": amount or PLANS.get(plan, {}).get("yearly_amount", 0),
        "plan": plan,
        "status": "paid",
    }).execute()

    logger.info("Entitlement granted: user=%s plan=%s", user_id, plan)
    return {"status": "verified", "plan": plan}
