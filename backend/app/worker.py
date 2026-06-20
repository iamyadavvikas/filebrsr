"""
Background Extraction Worker
==============================
Polls `extraction_jobs` table for queued jobs and processes them.
Runs as a separate process alongside the main API.

Usage:
  python -m app.worker
"""

import asyncio
import logging
from datetime import datetime

from app.brsr_datapoints import analyze_gaps_v2, get_datapoints_stats
from app.config import get_settings
from app.extraction_pipeline import run_full_extraction
from app.nifty50_benchmarks import get_benchmark_comparison

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [worker] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("worker")

settings = get_settings()

POLL_INTERVAL = 3  # seconds
MAX_CONCURRENT = 2  # max parallel extractions


def get_supabase():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def process_job(job: dict) -> None:
    """Process a single extraction job."""
    sb = get_supabase()
    job_id = job["id"]
    report_id = job["report_id"]
    file_url = job["file_url"]
    user_id = job.get("user_id")

    logger.info("Processing job %s (report: %s)", job_id, report_id)

    # Mark as processing
    sb.table("extraction_jobs").update({
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
    }).eq("id", job_id).execute()

    try:
        # Download file from Supabase Storage
        file_bytes = sb.storage.from_("brsr-reports").download(file_url)
        if not file_bytes:
            raise Exception("Could not download file from storage")

        # Unified pipeline (Phase 5.1). Worker now picks up OCR, citations
        # and opt-in retrieval — capabilities the legacy pdfplumber-only
        # worker was missing. 80-page cap preserves free-tier LLM quota.
        result = await run_full_extraction(
            file_bytes=file_bytes,
            settings=settings,
            report_id=report_id,
            user_id=user_id,
            supabase_client=sb,
            max_pages=80,
        )

        if result["status"] != "completed":
            raise Exception(result["error"] or "Extraction failed")

        merged = result["extracted_data"]
        confidence = result["confidence_scores"]
        company_name = result["company_name"]
        financial_year = result["financial_year"]
        benchmark = get_benchmark_comparison(merged)
        gap_analysis = analyze_gaps_v2(merged)
        datapoints_stats = get_datapoints_stats()

        full_extracted = {
            **merged,
            "gap_analysis": gap_analysis,
            "datapoints_stats": datapoints_stats,
            "benchmark": benchmark,
        }

        # Update report
        sb.table("reports").update({
            "status": "completed",
            "extracted_data": full_extracted,
            "confidence_scores": confidence,
            "company_name": company_name,
            "financial_year": financial_year,
        }).eq("id", report_id).execute()

        # Mark job complete
        sb.table("extraction_jobs").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", job_id).execute()

        logger.info("Job %s completed successfully", job_id)

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, str(e))
        sb.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
        sb.table("extraction_jobs").update({
            "status": "failed",
            "error": str(e)[:500],
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", job_id).execute()


async def worker_loop():
    """Main worker loop — polls for queued jobs."""
    logger.info("Worker started. Polling every %ds for queued jobs...", POLL_INTERVAL)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    while True:
        try:
            sb = get_supabase()
            # Fetch queued jobs (oldest first)
            result = sb.table("extraction_jobs").select("*").eq(
                "status", "queued"
            ).order("created_at").limit(MAX_CONCURRENT).execute()

            jobs = result.data or []

            if jobs:
                logger.info("Found %d queued job(s)", len(jobs))
                tasks = []
                for job in jobs:
                    async def _run(j=job):
                        async with semaphore:
                            await process_job(j)
                    tasks.append(asyncio.create_task(_run()))
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error("Worker poll error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


def main():
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
