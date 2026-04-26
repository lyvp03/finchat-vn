import logging
from typing import List
from ingest.news.models import NewsArticle
from ingest.news.repositories.gold_news_repository import GoldNewsRepository

logger = logging.getLogger("news_dedupe_service")

class NewsDedupeService:
    def __init__(self, repository: GoldNewsRepository):
        self.repository = repository
        
    def filter_new_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Lọc ra các bài báo hoàn toàn mới, loại bỏ những bài đã tồn tại trong DB.
        Sử dụng bulk checking để tối ưu hiệu suất.
        """
        if not articles:
            return []
            
        # 1. Trích xuất danh sách các canonical_url cần kiểm tra
        urls_to_check = [article.canonical_url for article in articles if article.canonical_url]
        
        # 2. Truy vấn DB 1 lần để lấy các URL đã tồn tại
        existing_urls = self.repository.get_existing_urls(urls_to_check)
        
        # 3. Lọc danh sách bài báo
        new_articles = []
        for article in articles:
            if article.canonical_url in existing_urls:
                logger.info(f"Duplicate skipped: {article.title}")
                continue
            new_articles.append(article)
            
        return new_articles
