"""
Tracking Service - Async job management for filing tracking
"""
import asyncio
import os
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import re
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db_session
from models.job import TrackingJob
from models.filing import Filing
from models.analysis import AnalysisResult
from schemas.tracking import TrackJobStatus, FilingList, FilingResponse, AnalysisResponse
from cache.redis_client import cache


_executor = ThreadPoolExecutor(max_workers=2)
_analysis_executor = ThreadPoolExecutor(max_workers=4)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_tags = {"script", "style", "meta", "link"}
        self._current_tag: Optional[str] = None

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        self._current_tag = tag
        if tag in {"br", "p", "div", "tr"}:
            self._chunks.append("\n")
        elif tag == "td":
            self._chunks.append(" | ")

    def handle_data(self, data):  # noqa: ANN001
        if self._current_tag in self._skip_tags:
            return
        text = (data or "").strip()
        if text:
            self._chunks.append(text)

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in {"p", "div", "table"}:
            self._chunks.append("\n")

    def get_text(self) -> str:
        return " ".join(self._chunks)


def _extract_text_from_html(html_content: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html_content)
    text = parser.get_text()
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def _get_openrouter_models() -> list[str]:
    """
    Determine the list of models to use for analysis.

    Supports model rotation via either:
    - OPENROUTER_MODEL_ROTATION="modelA,modelB,..."
    - OPENROUTER_MODEL_SLOT_1..9 (in numeric order)
    - OPENROUTER_MODEL (single model)
    """
    rotation = os.getenv("OPENROUTER_MODEL_ROTATION", "").strip()
    if rotation:
        models = [m.strip() for m in rotation.split(",") if m.strip()]
        return models

    slot_models: list[str] = []
    for i in range(1, 10):
        raw = os.getenv(f"OPENROUTER_MODEL_SLOT_{i}", "").strip()
        if raw:
            slot_models.append(raw)
    if slot_models:
        return slot_models

    single = os.getenv("OPENROUTER_MODEL", "").strip()
    if single:
        return [single]

    # Fall back to API settings default (non-interactive)
    try:
        from api.config import get_settings

        settings = get_settings()
        if getattr(settings, "openrouter_model", None):
            return [settings.openrouter_model]
    except Exception:
        pass

    return []


async def _choose_openrouter_model() -> Optional[str]:
    models = _get_openrouter_models()
    if not models:
        return None
    if len(models) == 1:
        return models[0]

    # Prefer round-robin using Redis; fall back to random if Redis is unavailable.
    try:
        from cache.redis_client import get_redis_client

        redis = await get_redis_client()
        counter = await redis.incr("openrouter:model_rotation_counter")
        return models[(counter - 1) % len(models)]
    except Exception:
        return models[secrets.randbelow(len(models))]


def _get_openrouter_api_key() -> Optional[str]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    try:
        from api.config import get_settings

        settings = get_settings()
        return getattr(settings, "openrouter_api_key", None)
    except Exception:
        return None


def _openrouter_extra_headers() -> dict:
    """
    Extra per-request OpenRouter headers.
    Example: OPENROUTER_EXTRA_HEADERS_JSON='{"X-Provider":"Targon,Chutes"}'
    """
    raw = os.getenv("OPENROUTER_EXTRA_HEADERS_JSON", "").strip()
    if not raw:
        return {}
    try:
        import json

        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _openrouter_chat_completion(*, api_key: str, model: str, prompt: str) -> tuple[str, Optional[int]]:
    import httpx
    from openai import OpenAI

    http_client = httpx.Client(
        timeout=httpx.Timeout(90.0),
        headers={
            # Optional: helps OpenRouter attribute traffic.
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://github.com/undeemed/SEC-Tracker"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "SEC-Tracker API"),
        },
    )
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        http_client=http_client,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        extra_headers=_openrouter_extra_headers(),
    )

    content = getattr(getattr(response.choices[0], "message", None), "content", None)
    if not content:
        raise ValueError("OpenRouter returned an empty response")

    usage = getattr(response, "usage", None)
    total_tokens = getattr(usage, "total_tokens", None) if usage is not None else None
    return content, total_tokens


def _get_openrouter_model_from_slot(slot: int) -> Optional[str]:
    if slot < 1 or slot > 9:
        return None
    value = (os.getenv(f"OPENROUTER_MODEL_SLOT_{slot}") or "").strip()
    return value or None


_MODEL_RE = re.compile(r"^[A-Za-z0-9._:/+\-]+$")


def _validate_openrouter_model_name(value: str) -> str:
    model = (value or "").strip()
    if not model:
        raise ValueError("model must be a non-empty string")
    if len(model) > 200:
        raise ValueError("model is too long")
    if not _MODEL_RE.match(model):
        raise ValueError("model contains invalid characters")
    return model


class TrackingService:
    """Service for tracking SEC filings."""
    
    async def start_tracking_job(
        self,
        user_id: UUID,
        ticker: str,
        forms: Optional[List[str]] = None,
        analyze: bool = True
    ) -> UUID:
        """Create a new tracking job."""
        async for db in get_db_session():
            job = TrackingJob(
                id=uuid4(),
                user_id=user_id,
                job_type="track",
                status="queued",
                ticker=ticker.upper(),
                progress=0,
                message=f"Tracking job created for {ticker.upper()}",
                result={"forms": forms or [], "analyze": analyze}
            )
            
            db.add(job)
            await db.commit()
            
            return job.id
    
    async def run_tracking_job(self, job_id: UUID):
        """Execute tracking job in background."""
        async for db in get_db_session():
            # Get job
            result = await db.execute(
                select(TrackingJob).where(TrackingJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return
            
            try:
                # Update status
                job.status = "processing"
                job.started_at = datetime.utcnow()
                job.progress = 10
                job.message = "Fetching filings..."
                await db.commit()
                
                # Run sync tracking code
                loop = asyncio.get_event_loop()
                result_data = await loop.run_in_executor(
                    _executor,
                    self._run_tracking,
                    job.ticker,
                    job.result.get("forms"),
                    job.result.get("analyze", True)
                )
                
                # Update job with results
                job.status = "complete"
                job.progress = 100
                job.completed_at = datetime.utcnow()
                job.result = result_data
                job.message = f"Completed: {result_data.get('filings_count', 0)} filings processed"
                
                await db.commit()
                
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                await db.commit()
    
    def _run_tracking(
        self,
        ticker: str,
        forms: Optional[List[str]],
        analyze: bool
    ) -> dict:
        """Run tracking logic synchronously."""
        from core.tracker import FilingTracker, download_new_filings

        tracker = FilingTracker()
        before = set((tracker.state.get("filings") or {}).keys())

        # Download filings (returns bool)
        downloaded = download_new_filings(tracker, ticker)
        after = tracker.state.get("filings") or {}

        new_accessions = [a for a in after.keys() if a not in before] if downloaded else []

        result: dict = {
            "ticker": ticker,
            "filings_count": 0,
            "filings": [],
            "analyzed": False,
        }

        # Optionally filter by requested forms
        wanted_forms = set(f.upper() for f in (forms or []) if f) if forms else None

        for accession in new_accessions:
            meta = after.get(accession) or {}
            form_type = (meta.get("form") or "").upper()
            if wanted_forms is not None and form_type not in wanted_forms:
                continue

            result["filings"].append(
                {
                    "form_type": form_type or None,
                    "accession": accession,
                    "date": meta.get("filing_date"),
                    "doc_url": meta.get("doc_url"),
                }
            )

        result["filings_count"] = len(result["filings"])

        # Analysis pipeline is not implemented in the API service layer yet.
        # Keep the flag false so clients don't assume analysis ran.
        result["analyzed"] = False

        return result
    
    async def get_job_status(self, job_id: UUID, user_id: UUID) -> Optional[TrackJobStatus]:
        """Get status of a tracking job."""
        async for db in get_db_session():
            result = await db.execute(
                select(TrackingJob).where(
                    TrackingJob.id == job_id,
                    TrackingJob.user_id == user_id
                )
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return None
            
            return TrackJobStatus(
                job_id=job.id,
                status=job.status,
                progress=job.progress,
                message=job.message,
                ticker=job.ticker,
                filings_found=job.result.get("filings_count", 0) if job.result else 0,
                filings_downloaded=job.result.get("filings_count", 0) if job.result else 0,
                filings_analyzed=1 if job.result and job.result.get("analyzed") else 0,
                error=job.error,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                result=job.result
            )
    
    async def get_user_filings(
        self,
        user_id: UUID,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> FilingList:
        """Get filings for user's tracked companies."""
        async for db in get_db_session():
            tickers_result = await db.execute(
                select(TrackingJob.ticker)
                .where(
                    TrackingJob.user_id == user_id,
                    TrackingJob.ticker.is_not(None),
                )
                .distinct()
            )
            user_tickers = sorted({t[0] for t in tickers_result.all() if t and t[0]})

            if ticker:
                requested = ticker.upper()
                if requested not in user_tickers:
                    return FilingList(filings=[], total=0, limit=limit, offset=offset)

            if not user_tickers:
                return FilingList(filings=[], total=0, limit=limit, offset=offset)

            query = select(Filing)

            query = query.where(Filing.ticker.in_(user_tickers))

            if ticker:
                query = query.where(Filing.ticker == ticker.upper())
            
            if form_type:
                query = query.where(Filing.form_type == form_type)
            
            query = query.order_by(Filing.filing_date.desc())
            query = query.limit(limit).offset(offset)
            
            result = await db.execute(query)
            filings = result.scalars().all()
            
            filing_responses = [
                FilingResponse(
                    id=f.id,
                    ticker=f.ticker,
                    cik=f.cik,
                    accession_number=f.accession_number,
                    form_type=f.form_type,
                    filing_date=f.filing_date,
                    description=f.description,
                    document_url=f.document_url,
                    has_analysis=bool(f.analysis_results)
                )
                for f in filings
            ]
            
            return FilingList(
                filings=filing_responses,
                total=len(filing_responses),
                limit=limit,
                offset=offset
            )
    
    async def get_analysis(
        self,
        filing_id: UUID,
        user_id: UUID
    ) -> Optional[AnalysisResponse]:
        """Get analysis for a filing.
        
        SECURITY: Only returns analysis if user owns it or it's public.
        """
        async for db in get_db_session():
            # Join with user check to prevent unauthorized access
            result = await db.execute(
                select(AnalysisResult, Filing)
                .join(Filing)
                .where(
                    AnalysisResult.filing_id == filing_id,
                    AnalysisResult.user_id == user_id  # SECURITY: Check ownership
                )
            )
            row = result.first()
            
            if not row:
                return None
            
            analysis, filing = row
            
            return AnalysisResponse(
                id=analysis.id,
                filing_id=analysis.filing_id,
                ticker=filing.ticker,
                form_type=filing.form_type,
                model_used=analysis.model_used,
                sentiment=analysis.sentiment,
                analysis_text=analysis.analysis_text,
                key_findings=analysis.key_findings,
                tokens_used=analysis.tokens_used,
                created_at=analysis.created_at
            )
    
    async def start_analysis_job(
        self,
        user_id: UUID,
        filing_id: UUID,
        force: bool = False,
        model_slot: Optional[int] = None,
        model: Optional[str] = None,
    ) -> UUID:
        """Start an analysis job for a filing."""
        async for db in get_db_session():
            validated_model = None
            if model is not None:
                validated_model = _validate_openrouter_model_name(model)

            job = TrackingJob(
                id=uuid4(),
                user_id=user_id,
                job_type="analyze",
                status="queued",
                progress=0,
                message=f"Analysis job created",
                result={
                    "filing_id": str(filing_id),
                    "force": force,
                    "model_slot": model_slot,
                    "model": validated_model,
                }
            )
            
            db.add(job)
            await db.commit()
            
            return job.id
    
    async def run_analysis_job(self, job_id: UUID):
        """Execute analysis job in background."""
        async for db in get_db_session():
            result = await db.execute(
                select(TrackingJob).where(TrackingJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                return

            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.progress = 10
            job.message = "Starting analysis..."
            await db.commit()

            try:
                api_key = _get_openrouter_api_key()
                if not api_key:
                    raise RuntimeError("OPENROUTER_API_KEY is not configured")

                if not job.result or not job.result.get("filing_id"):
                    raise RuntimeError("Job is missing filing_id")

                filing_id = UUID(str(job.result["filing_id"]))
                force = bool(job.result.get("force", False))

                filing_result = await db.execute(select(Filing).where(Filing.id == filing_id))
                filing = filing_result.scalar_one_or_none()
                if filing is None:
                    raise RuntimeError("Filing not found")

                # If analysis already exists and force is false, return existing.
                existing_result = await db.execute(
                    select(AnalysisResult).where(
                        AnalysisResult.filing_id == filing_id,
                        AnalysisResult.user_id == job.user_id,
                    )
                )
                existing = existing_result.scalar_one_or_none()
                if existing is not None and not force:
                    job.status = "complete"
                    job.progress = 100
                    job.completed_at = datetime.utcnow()
                    job.message = "Analysis already exists"
                    job.result = {"analysis_id": str(existing.id), "filing_id": str(filing_id)}
                    await db.commit()
                    return

                job.progress = 25
                job.message = "Loading filing content..."
                await db.commit()

                text_content = None
                if filing.raw_content:
                    text_content = _extract_text_from_html(filing.raw_content)
                else:
                    # Try local filesystem (legacy downloader layout).
                    from pathlib import Path

                    accession = filing.accession_number
                    form_type = filing.form_type
                    candidates = [
                        Path("sec_filings") / str(filing.ticker) / str(form_type) / f"{accession}.html",
                        Path("sec_filings") / f"CIK{str(filing.cik)}" / str(form_type) / f"{accession}.html",
                    ]
                    for path in candidates:
                        if path.exists():
                            raw = path.read_bytes()
                            try:
                                html = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                html = raw.decode("latin-1", errors="replace")
                            text_content = _extract_text_from_html(html)
                            break

                # Fall back to downloading document_url if present.
                if not text_content and filing.document_url:
                    import httpx

                    from utils.config import get_user_agent

                    headers = {"User-Agent": get_user_agent()}
                    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
                        resp = await client.get(filing.document_url)
                        resp.raise_for_status()
                        text_content = _extract_text_from_html(resp.text)

                if not text_content:
                    raise RuntimeError(
                        "No filing content available (raw_content missing, local file missing, and document_url missing/unfetchable)."
                    )

                max_chars = int(os.getenv("ANALYSIS_MAX_CHARS", "200000"))
                if len(text_content) > max_chars:
                    text_content = text_content[:max_chars]

                requested_slot = None
                requested_model = None
                if job.result:
                    requested_slot = job.result.get("model_slot")
                    requested_model = job.result.get("model")

                model = None
                if requested_model:
                    model = _validate_openrouter_model_name(str(requested_model))
                elif requested_slot is not None:
                    try:
                        slot_int = int(requested_slot)
                    except Exception:
                        raise RuntimeError("model_slot must be an integer between 1 and 9")

                    model = _get_openrouter_model_from_slot(slot_int)
                    if not model:
                        raise RuntimeError(f"OPENROUTER_MODEL_SLOT_{slot_int} is not configured")
                else:
                    model = await _choose_openrouter_model()
                if not model:
                    raise RuntimeError("No OpenRouter model configured (set OPENROUTER_MODEL or rotation vars)")

                job.progress = 60
                job.message = f"Calling OpenRouter model: {model}"
                await db.commit()

                prompt = (
                    "Analyze this SEC filing excerpt and provide a concise, structured summary.\n\n"
                    f"Ticker: {filing.ticker}\n"
                    f"CIK: {filing.cik}\n"
                    f"Form Type: {filing.form_type}\n"
                    f"Filing Date: {filing.filing_date}\n"
                    f"Accession: {filing.accession_number}\n\n"
                    "Return:\n"
                    "1) Executive summary (5-10 bullets)\n"
                    "2) Key risks (bullets)\n"
                    "3) Key catalysts/opportunities (bullets)\n"
                    "4) Any notable quantitative figures (bullets)\n\n"
                    "Filing text:\n"
                    f"{text_content}"
                )

                loop = asyncio.get_running_loop()
                analysis_text, tokens_used = await loop.run_in_executor(
                    _analysis_executor,
                    lambda: _openrouter_chat_completion(api_key=api_key, model=model, prompt=prompt),
                )

                # Derive a basic sentiment/key_findings summary.
                sentiment = None
                key_findings = None
                try:
                    from core.tracker import extract_sentiment_from_text

                    summary = extract_sentiment_from_text(analysis_text, filing.form_type)
                    sentiment = (summary.get("sentiment") or "").lower() or None
                    key_findings = summary
                except Exception:
                    pass

                job.progress = 90
                job.message = "Saving analysis..."
                await db.commit()

                # Upsert behavior: if force=True and an existing record exists, replace it.
                if existing is not None and force:
                    existing.model_used = model
                    existing.analysis_text = analysis_text
                    existing.sentiment = sentiment
                    existing.key_findings = key_findings
                    existing.tokens_used = tokens_used
                    analysis_row = existing
                else:
                    analysis_row = AnalysisResult(
                        id=uuid4(),
                        filing_id=filing.id,
                        user_id=job.user_id,
                        model_used=model,
                        analysis_text=analysis_text,
                        sentiment=sentiment,
                        key_findings=key_findings,
                        tokens_used=tokens_used,
                        created_at=datetime.utcnow(),
                    )
                    db.add(analysis_row)

                await db.commit()

                job.status = "complete"
                job.progress = 100
                job.completed_at = datetime.utcnow()
                job.message = "Analysis complete"
                job.result = {
                    "analysis_id": str(analysis_row.id),
                    "filing_id": str(filing.id),
                    "model_used": model,
                }
                await db.commit()

            except Exception as e:
                job.status = "failed"
                job.progress = 100
                job.error = str(e)
                job.message = "Analysis job failed"
                job.completed_at = datetime.utcnow()
                await db.commit()
