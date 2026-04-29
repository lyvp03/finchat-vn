from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

import hashlib

@dataclass
class NewsArticle:
    id: str = ""
    # Cơ bản
    title: str = ""
    summary: str = ""
    content: str = ""
    
    # Nguồn
    source_name: str = ""
    source_type: str = ""  # rss, api, scrape
    url: str = ""
    canonical_url: str = ""
    author: str = ""
    
    # Thời gian
    published_at: datetime = field(default_factory=datetime.now)
    crawled_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Phân loại
    category: str = ""
    language: str = "vi"
    region: str = "vn"
    event_type: str = ""
    market_scope: str = ""  # domestic, international, mixed
    
    # Entity/tags
    symbols: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    
    # NLP / AI Scores
    sentiment_score: float = 0.0
    impact_score: float = 0.0
    relevance_score: float = 0.0
    
    # Hệ thống
    title_hash: str = ""
    content_hash: str = ""
    quality_score: float = 1.0
    is_relevant: bool = True
    is_duplicate: bool = False
    raw_payload: str = ""
    extra_metadata: str = ""
    news_tier: str = "contextual"  # direct | contextual | weak

    def generate_hashes(self):
        """Chuẩn hóa URL và sinh hash. Content hash fallback khi content rỗng/ngắn."""
        if not self.canonical_url and self.url:
            self.canonical_url = self.url.split('?')[0].split('#')[0]
            
        if self.title:
            self.title_hash = hashlib.sha256(self.title.encode('utf-8')).hexdigest()
            
        # Content hash: fallback nếu content rỗng hoặc quá ngắn
        if self.content and len(self.content) >= 50:
            self.content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
        else:
            fallback = (self.title or "") + (self.summary or "") + (self.canonical_url or "")
            self.content_hash = hashlib.sha256(fallback.encode('utf-8')).hexdigest()
            
        if self.canonical_url:
            self.id = hashlib.sha256(self.canonical_url.encode('utf-8')).hexdigest()
