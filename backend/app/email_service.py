"""
Email Notification Service for FileBRSR.
Handles: assessment invites, filing reminders, deadline alerts, team notifications.
Uses Resend API (free tier: 100 emails/day).
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from app.config import get_settings

settings = get_settings()

RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = "FileBRSR <notifications@filebrsr.com>"

# Email templates
TEMPLATES = {
    "team_invite": {
        "subject": "You've been invited to join {org_name} on FileBRSR",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
                <p style="color: #6B7280; font-size: 14px;">BRSR Compliance Platform</p>
            </div>
            <div style="background: #F0FDF4; border-radius: 12px; padding: 30px; border: 1px solid #BBF7D0;">
                <h2 style="color: #1B4D3E; margin-top: 0;">You're invited!</h2>
                <p style="color: #374151; line-height: 1.6;">
                    <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong>
                    as a <strong>{role}</strong> on FileBRSR.
                </p>
                <p style="color: #6B7280; font-size: 14px;">
                    FileBRSR helps Indian companies automate BRSR (Business Responsibility & Sustainability Reporting)
                    compliance with AI-powered extraction and real-time tracking.
                </p>
                <a href="{invite_url}" style="display: inline-block; background: #1B4D3E; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 16px;">
                    Accept Invitation
                </a>
                <p style="color: #9CA3AF; font-size: 12px; margin-top: 20px;">
                    This invite expires in 7 days. If you didn't expect this, you can ignore this email.
                </p>
            </div>
        </div>
        """,
    },
    "filing_reminder": {
        "subject": "[Action Required] BRSR Filing Deadline: {deadline_date}",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
            </div>
            <div style="background: #FEF3C7; border-radius: 12px; padding: 30px; border: 1px solid #FDE68A;">
                <h2 style="color: #92400E; margin-top: 0;">⚠️ Filing Deadline Approaching</h2>
                <p style="color: #374151; line-height: 1.6;">
                    Your BRSR filing for <strong>{financial_year}</strong> is due on
                    <strong>{deadline_date}</strong> ({days_remaining} days remaining).
                </p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;"><strong>Completion:</strong> {completion_pct}% of mandatory datapoints filled</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Pending Review:</strong> {pending_review} items awaiting approval</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Exchange:</strong> {exchange}</p>
                </div>
                <a href="https://filebrsr.com/platform/data-entry" style="display: inline-block; background: #92400E; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Complete Filing →
                </a>
            </div>
        </div>
        """,
    },
    "extraction_complete": {
        "subject": "✅ BRSR Extraction Complete — {file_name}",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
            </div>
            <div style="background: #F0FDF4; border-radius: 12px; padding: 30px; border: 1px solid #BBF7D0;">
                <h2 style="color: #166534; margin-top: 0;">✅ Extraction Complete</h2>
                <p style="color: #374151; line-height: 1.6;">
                    Your PDF <strong>{file_name}</strong> has been processed successfully.
                </p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;"><strong>Datapoints Extracted:</strong> {datapoints_count}</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Avg Confidence:</strong> {avg_confidence}%</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Compliance Score:</strong> {compliance_score}%</p>
                </div>
                <a href="https://filebrsr.com/platform/reports/{report_id}" style="display: inline-block; background: #1B4D3E; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    View Results →
                </a>
            </div>
        </div>
        """,
    },
    "workflow_action": {
        "subject": "[{action}] {entity_type} requires your attention",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
            </div>
            <div style="background: #EFF6FF; border-radius: 12px; padding: 30px; border: 1px solid #BFDBFE;">
                <h2 style="color: #1E40AF; margin-top: 0;">📋 Approval Required</h2>
                <p style="color: #374151; line-height: 1.6;">
                    <strong>{initiator_name}</strong> has submitted a <strong>{entity_type}</strong>
                    for your review and approval.
                </p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;"><strong>Item:</strong> {entity_description}</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Your Role:</strong> {reviewer_role}</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Submitted:</strong> {submitted_at}</p>
                </div>
                <a href="https://filebrsr.com/platform/workflows" style="display: inline-block; background: #1E40AF; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Review Now →
                </a>
            </div>
        </div>
        """,
    },
    "deadline_alert": {
        "subject": "🔴 {regulation} compliance deadline in {days_remaining} days",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
            </div>
            <div style="background: #FEF2F2; border-radius: 12px; padding: 30px; border: 1px solid #FECACA;">
                <h2 style="color: #991B1B; margin-top: 0;">🔴 Deadline Alert</h2>
                <p style="color: #374151; line-height: 1.6;">
                    <strong>{regulation}</strong> compliance deadline is in <strong>{days_remaining} days</strong>
                    ({deadline_date}).
                </p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;"><strong>Status:</strong> {current_status}</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Financial Year:</strong> {financial_year}</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Filing Authority:</strong> {authority}</p>
                </div>
                <a href="https://filebrsr.com/platform/compliance" style="display: inline-block; background: #991B1B; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    View Compliance →
                </a>
            </div>
        </div>
        """,
    },
    "supplier_invite": {
        "subject": "{buyer_company} needs your ESG assessment",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
                <p style="color: #6B7280; font-size: 14px;">Supply Chain ESG Platform</p>
            </div>
            <div style="background: #EFF6FF; border-radius: 12px; padding: 30px; border: 1px solid #BFDBFE;">
                <h2 style="color: #1E40AF; margin-top: 0;">ESG Assessment Request</h2>
                <p style="color: #374151; line-height: 1.6;">
                    Hi {contact_person},
                </p>
                <p style="color: #374151; line-height: 1.6;">
                    <strong>{buyer_company}</strong> has requested an ESG assessment of <strong>{supplier_name}</strong>
                    as part of their SEBI BRSR supply chain disclosure requirements.
                </p>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;">✓ Takes only <strong>5 minutes</strong></p>
                    <p style="margin: 4px 0; color: #374151;">✓ <strong>No signup</strong> required</p>
                    <p style="margin: 4px 0; color: #374151;">✓ Get a <strong>free ESG scorecard</strong> & badge</p>
                    <p style="margin: 4px 0; color: #374151;">✓ Prove ESG readiness to <strong>all your buyers</strong></p>
                </div>
                <a href="{assessment_url}" style="display: inline-block; background: #1B4D3E; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 15px;">
                    Complete Assessment →
                </a>
                <p style="color: #9CA3AF; font-size: 12px; margin-top: 20px;">
                    This assessment is confidential. Only aggregated scores are shared with {buyer_company}.
                    Fill once — your badge works for all buyers.
                </p>
            </div>
        </div>
        """,
    },
    "readiness_report": {
        "subject": "Your BRSR Readiness Score: {score}% ({readiness_level})",
        "html": """
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B4D3E; font-size: 24px; margin: 0;">FileBRSR</h1>
            </div>
            <div style="background: #F0FDF4; border-radius: 12px; padding: 30px; border: 1px solid #BBF7D0;">
                <h2 style="color: #166534; margin-top: 0;">Your BRSR Readiness Report</h2>
                <p style="color: #374151; line-height: 1.6;">
                    Hi {name}, here's your readiness assessment for <strong>{company}</strong>:
                </p>
                <div style="text-align: center; margin: 24px 0;">
                    <div style="display: inline-block; width: 100px; height: 100px; border-radius: 50%; border: 6px solid #059669; line-height: 88px; font-size: 28px; font-weight: 800; color: #059669;">
                        {score}%
                    </div>
                    <p style="font-size: 18px; font-weight: 700; color: #374151; margin-top: 8px;">{readiness_level}</p>
                </div>
                <div style="background: white; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #374151;"><strong>BRSR Filing:</strong> {phase_scores[phase1]}%</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Supply Chain ESG:</strong> {phase_scores[phase2]}%</p>
                    <p style="margin: 4px 0; color: #374151;"><strong>Carbon Market:</strong> {phase_scores[phase3]}%</p>
                </div>
                <a href="https://filebrsr.com/signup" style="display: inline-block; background: #1B4D3E; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Start Closing Gaps →
                </a>
                <p style="color: #9CA3AF; font-size: 12px; margin-top: 20px;">
                    FY2026-27 deadline approaching. Companies scoring below 60% face compliance risk.
                </p>
            </div>
        </div>
        """,
    },
    "admin_pilot_notification": {
        "subject": "🚀 New Pilot Application: {company_name}",
        "html": """
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 12px; padding: 24px;">
                <h2 style="color: #166534; margin: 0 0 16px;">New Pilot Application Received</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 6px 0; color: #6B7280; width: 140px;">Company</td><td style="padding: 6px 0; font-weight: 600; color: #111827;">{company_name}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Contact</td><td style="padding: 6px 0; color: #111827;">{contact_name}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Email</td><td style="padding: 6px 0; color: #111827;">{email}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Designation</td><td style="padding: 6px 0; color: #111827;">{designation}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">CIN</td><td style="padding: 6px 0; color: #111827;">{cin}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Market Cap</td><td style="padding: 6px 0; color: #111827;">{market_cap_range}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Current Method</td><td style="padding: 6px 0; color: #111827;">{current_method}</td></tr>
                    <tr><td style="padding: 6px 0; color: #6B7280;">Pain Points</td><td style="padding: 6px 0; color: #111827;">{pain_points}</td></tr>
                </table>
                <p style="color: #6B7280; font-size: 12px; margin-top: 16px;">Submitted at {submitted_at}</p>
            </div>
        </div>
        """,
    },
}

ADMIN_EMAIL = "support@filebrsr.com"


async def send_email(
    to: str,
    template_name: str,
    variables: dict,
    resend_api_key: Optional[str] = None,
) -> dict:
    """Send an email using Resend API with a named template."""
    api_key = resend_api_key or getattr(settings, "RESEND_API_KEY", None)
    if not api_key:
        # Graceful degradation — log instead of failing
        print(f"[EMAIL] Would send '{template_name}' to {to} — RESEND_API_KEY not set")
        return {"status": "skipped", "reason": "no_api_key"}

    template = TEMPLATES.get(template_name)
    if not template:
        return {"status": "error", "reason": f"template '{template_name}' not found"}

    subject = template["subject"].format(**variables)
    html = template["html"].format(**variables)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )

    if resp.status_code == 200:
        return {"status": "sent", "id": resp.json().get("id")}
    else:
        return {"status": "error", "code": resp.status_code, "body": resp.text}


async def send_team_invite(to_email: str, org_name: str, inviter_name: str, role: str, invite_token: str):
    """Send team invitation email."""
    return await send_email(to_email, "team_invite", {
        "org_name": org_name,
        "inviter_name": inviter_name,
        "role": role,
        "invite_url": f"https://filebrsr.com/platform/settings?invite={invite_token}",
    })


async def send_filing_reminder(to_email: str, financial_year: str, deadline_date: str, days_remaining: int, completion_pct: int, pending_review: int, exchange: str = "BSE + NSE"):
    """Send BRSR filing deadline reminder."""
    return await send_email(to_email, "filing_reminder", {
        "financial_year": financial_year,
        "deadline_date": deadline_date,
        "days_remaining": days_remaining,
        "completion_pct": completion_pct,
        "pending_review": pending_review,
        "exchange": exchange,
    })


async def send_extraction_complete(to_email: str, file_name: str, report_id: str, datapoints_count: int, avg_confidence: int, compliance_score: int):
    """Send notification when PDF extraction is done."""
    return await send_email(to_email, "extraction_complete", {
        "file_name": file_name,
        "report_id": report_id,
        "datapoints_count": datapoints_count,
        "avg_confidence": avg_confidence,
        "compliance_score": compliance_score,
    })


async def send_workflow_notification(to_email: str, action: str, entity_type: str, initiator_name: str, entity_description: str, reviewer_role: str, submitted_at: str):
    """Send workflow approval notification."""
    return await send_email(to_email, "workflow_action", {
        "action": action,
        "entity_type": entity_type,
        "initiator_name": initiator_name,
        "entity_description": entity_description,
        "reviewer_role": reviewer_role,
        "submitted_at": submitted_at,
    })


async def send_deadline_alert(to_email: str, regulation: str, days_remaining: int, deadline_date: str, current_status: str, financial_year: str, authority: str):
    """Send regulatory deadline alert."""
    return await send_email(to_email, "deadline_alert", {
        "regulation": regulation,
        "days_remaining": days_remaining,
        "deadline_date": deadline_date,
        "current_status": current_status,
        "financial_year": financial_year,
        "authority": authority,
    })
