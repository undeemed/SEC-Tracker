"""
Filing Tracking Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
from uuid import UUID

from api.dependencies import get_db, get_current_user
from api.config import get_settings
from schemas.tracking import (
    TrackRequest, TrackResponse, TrackJobStatus,
    FilingResponse, FilingList, AnalysisResponse
)
from services.tracking_service import TrackingService


router = APIRouter()


@router.post("/", response_model=TrackResponse, status_code=202)
async def start_tracking(
    request: TrackRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
):
    """
    Start tracking filings for a company.
    
    This initiates an async job that:
    1. Fetches recent SEC filings
    2. Downloads filing documents
    3. Runs AI analysis (if requested)
    
    - **ticker**: Stock ticker symbol
    - **forms**: List of form types to track (default: all)
    - **analyze**: Whether to run AI analysis
    
    Returns a job_id to poll for status.
    """
    service = TrackingService()
    
    try:
        job_id = await service.start_tracking_job(
            user_id=current_user.id,
            ticker=request.ticker.upper(),
            forms=request.forms,
            analyze=request.analyze
        )
        
        # Enqueue background work (Celery if enabled, otherwise FastAPI BackgroundTasks)
        settings = get_settings()
        if settings.celery_enabled:
            try:
                from services.worker import run_tracking_job_task
                run_tracking_job_task.delay(str(job_id))
            except Exception:
                background_tasks.add_task(service.run_tracking_job, job_id)
        else:
            background_tasks.add_task(service.run_tracking_job, job_id)
        
        return TrackResponse(
            job_id=job_id,
            status="queued",
            message=f"Tracking job started for {request.ticker.upper()}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job/{job_id}", response_model=TrackJobStatus)
async def get_job_status(
    job_id: UUID,
    current_user = Depends(get_current_user),
):
    """
    Get status of a tracking job.
    
    Returns current progress and any completed results.
    """
    service = TrackingService()
    
    job = await service.get_job_status(job_id, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history", response_model=FilingList)
async def get_filing_history(
    ticker: Optional[str] = Query(default=None, description="Filter by ticker"),
    form_type: Optional[str] = Query(default=None, description="Filter by form type"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user = Depends(get_current_user),
):
    """
    Get filing history for the current user's tracked companies.
    
    - **ticker**: Filter to specific company
    - **form_type**: Filter to specific form type (10-K, 8-K, etc.)
    - **limit**: Max results to return
    - **offset**: Pagination offset
    """
    service = TrackingService()
    
    filings = await service.get_user_filings(
        user_id=current_user.id,
        ticker=ticker,
        form_type=form_type,
        limit=limit,
        offset=offset
    )
    
    return filings


@router.get("/analysis/{filing_id}", response_model=AnalysisResponse)
async def get_filing_analysis(
    filing_id: UUID,
    current_user = Depends(get_current_user),
):
    """
    Get AI analysis for a specific filing.
    
    Returns the analysis text and key findings.
    """
    service = TrackingService()
    
    analysis = await service.get_analysis(filing_id, current_user.id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis


@router.post("/analyze/{filing_id}", response_model=TrackResponse, status_code=202)
async def request_analysis(
    filing_id: UUID,
    background_tasks: BackgroundTasks,
    force: bool = Query(default=False, description="Force re-analysis"),
    model_slot: Optional[int] = Query(
        default=None,
        ge=1,
        le=9,
        description="Force a specific OpenRouter model slot (OPENROUTER_MODEL_SLOT_1..9). If omitted, rotates.",
    ),
    model: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Force a specific OpenRouter model (overrides model_slot/rotation).",
    ),
    current_user = Depends(get_current_user),
):
    """
    Request AI analysis for a specific filing.
    
    If analysis already exists and force=False, returns existing.
    """
    service = TrackingService()
    
    job_id = await service.start_analysis_job(
        user_id=current_user.id,
        filing_id=filing_id,
        force=force,
        model_slot=model_slot,
        model=model,
    )
    
    settings = get_settings()
    if settings.celery_enabled:
        try:
            from services.worker import run_analysis_job_task
            run_analysis_job_task.delay(str(job_id))
        except Exception:
            background_tasks.add_task(service.run_analysis_job, job_id)
    else:
        background_tasks.add_task(service.run_analysis_job, job_id)
    
    return TrackResponse(
        job_id=job_id,
        status="queued",
        message="Analysis job started"
    )
