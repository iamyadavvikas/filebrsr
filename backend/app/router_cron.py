"""
Scheduled Tasks Router — Metrics rollup, filing reminders, housekeeping.

Endpoints are designed to be called by a cron job (e.g., GitHub Actions schedule,
AWS EventBridge, or a simple `curl` from crontab).

Protected by service role key.
"""

from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from app.config import get_settings

router = APIRouter(prefix="/api/cron", tags=["Scheduled Tasks"])
settings = get_settings()


def verify_service_key(authorization: str):
    """Only allow service-role calls."""
    expected = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized — service key required")


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# ═══════════════════════════════════════════════════════════════
# METRICS ROLLUP — Run daily at 00:05 UTC
# ═══════════════════════════════════════════════════════════════

@router.post("/metrics-rollup")
async def metrics_rollup(
    target_date: Optional[str] = None,
    authorization: str = Header(...),
):
    """
    Compute daily metrics from source tables and upsert into daily_metrics.
    Call with target_date=YYYY-MM-DD or omit for yesterday.
    """
    verify_service_key(authorization)
    sb = get_supabase_admin()

    if target_date:
        dt = date.fromisoformat(target_date)
    else:
        dt = date.today() - timedelta(days=1)

    day_start = datetime.combine(dt, datetime.min.time()).isoformat()
    day_end = datetime.combine(dt + timedelta(days=1), datetime.min.time()).isoformat()

    # 1. Total users (cumulative up to end of day)
    total_users = sb.table("profiles").select("id", count="exact").lte("created_at", day_end).execute()

    # 2. New signups on this day
    new_signups = sb.table("profiles").select("id", count="exact").gte("created_at", day_start).lt("created_at", day_end).execute()

    # 3. Active users (anyone who did extraction or data entry that day)
    active_extractors = sb.table("reports").select("user_id").gte("created_at", day_start).lt("created_at", day_end).execute()
    active_entries = sb.table("brsr_entries").select("user_id").gte("updated_at", day_start).lt("updated_at", day_end).execute()
    active_user_ids = set()
    for r in (active_extractors.data or []):
        if r.get("user_id"):
            active_user_ids.add(r["user_id"])
    for r in (active_entries.data or []):
        if r.get("user_id"):
            active_user_ids.add(r["user_id"])

    # 4. Extractions
    ext_started = sb.table("reports").select("id", count="exact").gte("created_at", day_start).lt("created_at", day_end).execute()
    ext_completed = sb.table("reports").select("id", count="exact").gte("created_at", day_start).lt("created_at", day_end).eq("status", "completed").execute()

    # 5. Data entries saved
    entries_saved = sb.table("brsr_entries").select("id", count="exact").gte("updated_at", day_start).lt("updated_at", day_end).execute()

    # 6. Revenue
    payments = sb.table("payments").select("amount").eq("status", "paid").gte("created_at", day_start).lt("created_at", day_end).execute()
    revenue = sum(p["amount"] for p in (payments.data or [])) / 100  # paise → INR

    # 7. Paid conversions
    paid_conversions = sb.table("payments").select("id", count="exact").eq("status", "paid").gte("created_at", day_start).lt("created_at", day_end).execute()

    # Upsert
    sb.table("daily_metrics").upsert({
        "date": dt.isoformat(),
        "total_users": total_users.count or 0,
        "new_signups": new_signups.count or 0,
        "active_users": len(active_user_ids),
        "extractions_started": ext_started.count or 0,
        "extractions_completed": ext_completed.count or 0,
        "data_entries_saved": entries_saved.count or 0,
        "reports_generated": ext_completed.count or 0,
        "paid_conversions": paid_conversions.count or 0,
        "revenue_inr": revenue,
    }, on_conflict="date").execute()

    return {
        "status": "ok",
        "date": dt.isoformat(),
        "metrics": {
            "total_users": total_users.count or 0,
            "new_signups": new_signups.count or 0,
            "active_users": len(active_user_ids),
            "extractions": ext_started.count or 0,
            "revenue_inr": revenue,
        },
    }


# ═══════════════════════════════════════════════════════════════
# FILING REMINDER — Run weekly on Monday at 09:00 IST
# ═══════════════════════════════════════════════════════════════

@router.post("/filing-reminders")
async def send_filing_reminders(authorization: str = Header(...)):
    """
    Send email reminders to users with incomplete BRSR filings.
    Only sends to users who haven't completed >50% of mandatory fields.
    """
    verify_service_key(authorization)
    sb = get_supabase_admin()

    # Get all users with their completion status
    profiles = sb.table("profiles").select("id, email, full_name, company_name").execute()
    reminders_sent = 0

    for profile in (profiles.data or []):
        if not profile.get("email"):
            continue

        # Check entry count
        entries = sb.table("brsr_entries").select("id", count="exact").eq("user_id", profile["id"]).execute()
        entry_count = entries.count or 0

        # Only remind if they started (>0 entries) but haven't completed much (<100 entries)
        if 0 < entry_count < 100:
            try:
                # Send via email service if available
                if settings.RESEND_API_KEY:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            "https://api.resend.com/emails",
                            headers={
                                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "from": "FileBRSR <reminders@filebrsr.com>",
                                "to": [profile["email"]],
                                "subject": f"BRSR Filing Reminder — {entry_count}/337 datapoints completed",
                                "html": f"""
                                <div style="font-family: system-ui; max-width: 600px; margin: 0 auto;">
                                    <h2 style="color: #059669;">FileBRSR Filing Reminder</h2>
                                    <p>Hi {profile.get('full_name', 'there')},</p>
                                    <p>Your BRSR filing for <strong>{profile.get('company_name', 'your company')}</strong>
                                    has <strong>{entry_count}/337</strong> datapoints completed ({round(entry_count/337*100)}%).</p>
                                    <p>SEBI filing deadlines are approaching. Complete your filing to avoid non-compliance.</p>
                                    <a href="https://filebrsr.com/platform/data-entry"
                                       style="display: inline-block; background: #059669; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                                        Continue Filing →
                                    </a>
                                    <p style="color: #666; font-size: 12px; margin-top: 24px;">
                                        You're receiving this because you started a BRSR filing on FileBRSR.
                                        <a href="https://filebrsr.com/platform/settings">Unsubscribe</a>
                                    </p>
                                </div>
                                """,
                            },
                        )
                    reminders_sent += 1
            except Exception:
                pass  # Don't fail the whole batch for one email

    return {"status": "ok", "reminders_sent": reminders_sent}


# ═══════════════════════════════════════════════════════════════
# BACKFILL — One-time: fill daily_metrics for historical data
# ═══════════════════════════════════════════════════════════════

@router.post("/metrics-backfill")
async def metrics_backfill(days: int = 30, authorization: str = Header(...)):
    """Backfill daily_metrics for the last N days."""
    verify_service_key(authorization)

    results = []
    for i in range(days, 0, -1):
        target = (date.today() - timedelta(days=i)).isoformat()
        result = await metrics_rollup(target_date=target, authorization=authorization)
        results.append(result)

    return {"status": "ok", "days_processed": len(results)}
