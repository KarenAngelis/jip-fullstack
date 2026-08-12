from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class NewsArticle(BaseModel):
    title: str
    url: str
    description: Optional[str] = None
    source: str
    published_date: Optional[str] = None
    image_url: Optional[str] = None
    content_preview: Optional[str] = None
    relevance_score: Optional[float] = None

class NewsSearchResponse(BaseModel):
    query: str
    total_results: int
    articles: List[NewsArticle]
    search_timestamp: datetime
    sources_used: List[str]

class NewsInsight(BaseModel):
    trend_analysis: str
    key_topics: List[str]
    sentiment: str  # positive, negative, neutral
    summary: str