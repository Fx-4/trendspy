from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    niche_input: str = Field(..., min_length=3, max_length=200, description="The niche or product idea to analyze")
    force: bool = Field(default=False, description="Skip cache and force fresh analysis")


class PainPoint(BaseModel):
    text: str
    frequency: int
    source: str


class CompetitorGap(BaseModel):
    competitor: str
    gap: str
    opportunity: str


class PricingSignals(BaseModel):
    competitor_range: str
    willingness_to_pay: str
    insights: list[str]


class Community(BaseModel):
    name: str
    members: str
    activity: str  # "high" | "medium" | "low"


class BriefResult(BaseModel):
    pain_points: list[PainPoint] = []
    competitor_gaps: list[CompetitorGap] = []
    pricing_signals: Optional[PricingSignals] = None
    hot_communities: list[Community] = []
    ai_summary: str = ""


class SaveBriefRequest(BaseModel):
    niche_input: str
    result: BriefResult


class BriefResponse(BaseModel):
    id: str
    niche_input: str
    pain_points: list[dict]
    competitor_gaps: list[dict]
    pricing_signals: dict
    hot_communities: list[dict]
    ai_summary: str
    is_public: bool
    share_slug: Optional[str]
    created_at: datetime
