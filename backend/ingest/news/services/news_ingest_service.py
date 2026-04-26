import logging
from ingest.news.sources.vnexpress import VnExpressCrawler
from ingest.news.parsers.vnexpress_parser import VnExpressParser
from ingest.news.repositories.gold_news_repository import GoldNewsRepository
from ingest.news.services.news_dedupe_service import NewsDedupeService

logger = logging.getLogger("news_ingest_service")

class NewsIngestService:
    def __init__(self, 
                 crawler: VnExpressCrawler, 
                 parser: VnExpressParser, 
                 repository: GoldNewsRepository, 
                 dedupe_service: NewsDedupeService):
        self.crawler = crawler
        self.parser = parser
        self.repository = repository
        self.dedupe_service = dedupe_service

    def run_incremental(self, limit: int = 30):
        """Chạy luồng thu thập tin tức mới (Incremental)"""
        logger.info(f"Starting incremental news ingest with limit={limit}")
        
        # 1. Fetch URLs
        urls = self.crawler.fetch_article_urls(limit=limit)
        if not urls:
            logger.info("No URLs found to process.")
            return

        # 2. Parse HTML
        parsed_articles = []
        for url in urls:
            html = self.crawler.fetch_article_html(url)
            if not html:
                continue
            
            article = self.parser.parse(url, html)
            if article:
                # Tạo hash và ID sau khi parse xong
                article.generate_hashes()
                parsed_articles.append(article)

        # 3. Deduplicate (Loại bỏ bài trùng)
        new_articles = self.dedupe_service.filter_new_articles(parsed_articles)
        
        # 4. Save to DB
        if new_articles:
            success = self.repository.save_bulk(new_articles)
            if success:
                logger.info(f"Successfully ingested {len(new_articles)} new articles.")
            else:
                logger.error("Failed to save new articles.")
        else:
            logger.info("No new articles to save.")
