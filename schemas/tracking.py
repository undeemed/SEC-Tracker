"""
Tracking Schemas
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class TrackRequest(BaseModel):
    """Request to track company filings."""
    ticker: str = Field(..., min_length=1, max_length=10)
    forms: Optional[List[str]] = Field(
        default=None,
        description="Form types to track (e.g., ['10-K', '8-K']). None = all"
    )
    analyze: bool = Field(
        default=True,
        description="Whether to run AI analysis"
    )


class TrackResponse(BaseModel):
    """Response when starting a tracking job."""
    job_id: UUID
    status: str
    message: str


class TrackJobStatus(BaseModel):
    """Status of a tracking job."""
    job_id: UUID
    status: str = Field(..., description="queued, processing, complete, failed")
    progress: int = Field(0, ge=0, le=100)
    message: Optional[str] = None
    ticker: Optional[str] = None
    filings_found: int = 0
    filings_downloaded: int = 0
    filings_analyzed: int = 0
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None


class FilingResponse(BaseModel):
    """Single filing response."""
    id: UUID
    ticker: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: date
    description: Optional[str] = None
    document_url: Optional[str] = None
    has_analysis: bool = False
    
    class Config:
        from_attributes = True


class FilingList(BaseModel):
    """Paginated filing list."""
    filings: List[FilingResponse]
    total: int
    limit: int
    offset: int


class AnalysisResponse(BaseModel):
    """AI analysis response."""
    id: UUID
    filing_id: UUID
    ticker: str
    form_type: str
    model_used: Optional[str] = None
    sentiment: Optional[str] = None
    analysis_text: Optional[str] = None
    key_findings: Optional[dict] = None
    tokens_used: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
