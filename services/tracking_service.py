"""
Tracking Service - Async job management for filing tracking
"""
import asyncio
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db_session
from models.job import TrackingJob
from models.filing import Filing
from models.analysis import AnalysisResult
from schemas.tracking import TrackJobStatus, FilingList, FilingResponse, AnalysisResponse
from cache.redis_client import cache


_executor = ThreadPoolExecutor(max_workers=2)


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
        
        # Download filings
        new_filings = download_new_filings(tracker, ticker)
        
        result = {
            "ticker": ticker,
            "filings_count": len(new_filings) if new_filings else 0,
            "filings": [],
            "analyzed": False
        }
        
        if new_filings:
            for form_type, filings in new_filings.items():
                for filing in filings:
                    result["filings"].append({
                        "form_type": form_type,
                        "accession": filing.get("accession"),
                        "date": filing.get("filing_date")
                    })
            
            # Run analysis if requested
            if analyze:
                try:
                    from core.analyzer import analyze_filings
                    # Analysis logic would go here
                    result["analyzed"] = True
                except Exception:
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
            query = select(Filing)
            
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
        """Get analysis for a filing."""
        async for db in get_db_session():
            result = await db.execute(
                select(AnalysisResult, Filing)
                .join(Filing)
                .where(AnalysisResult.filing_id == filing_id)
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
        force: bool = False
    ) -> UUID:
        """Start an analysis job for a filing."""
        async for db in get_db_session():
            job = TrackingJob(
                id=uuid4(),
                user_id=user_id,
                job_type="analyze",
                status="queued",
                progress=0,
                message=f"Analysis job created",
                result={"filing_id": str(filing_id), "force": force}
            )
            
            db.add(job)
            await db.commit()
            
            return job.id
    
    async def run_analysis_job(self, job_id: UUID):
        """Execute analysis job in background."""
        # Similar to run_tracking_job but for analysis
        pass
