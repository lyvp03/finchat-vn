import logging
from datetime import datetime
from ..models import NewsArticle

logger = logging.getLogger("reuters_parser")


class ReutersParser:
    """
    Parser cho bài viết Reuters từ Google News RSS.
    Vì Reuters chặn scraping (Cloudflare 401), parser chỉ tạo NewsArticle
    từ metadata RSS (title, date). Content sẽ = title (tạm thời).
    """
    SOURCE_NAME = "Reuters"

    def parse(self, url: str, html: str) -> NewsArticle:
        """
        Với Reuters, 'html' thực tế là URL (không fetch được HTML do captcha).
        Dữ liệu chính được lấy từ RSS cache của crawler.
        """
        # Method này sẽ được gọi bởi NewsIngestService
        # nhưng với Reuters ta không parse HTML được
        # -> trả về article cơ bản, sẽ được enrich bởi parse_from_rss
        return None

    def parse_from_rss(self, rss_item: dict) -> NewsArticle:
        """Tạo NewsArticle từ RSS metadata."""
        title = rss_item.get("title", "")
        link = rss_item.get("link", "")
        published_at = rss_item.get("published_at") or datetime.now()

        if not title:
            return None

        # Auto-detect symbols từ title
        symbols = []
        tags = ["gold"]
        title_lower = title.lower()
        if "gold" in title_lower or "xau" in title_lower:
            symbols.append("XAUUSD")
        if "silver" in title_lower:
            symbols.append("XAGUSD")
            tags.append("silver")
        if "fed" in title_lower or "federal reserve" in title_lower:
            tags.append("fed")
        if "inflation" in title_lower:
            tags.append("inflation")

        return NewsArticle(
            title=title,
            summary=title,  # RSS không có summary riêng
            content=title,  # Content = title (Reuters chặn body)
            source_name=self.SOURCE_NAME,
            source_type="rss",
            url=link,
            author="Reuters",
            published_at=published_at,
            category="commodities",
            language="en",
            region="us",
            symbols=symbols,
            tags=tags,
            quality_score=0.6,  # Thấp hơn vì thiếu content đầy đủ
        )
