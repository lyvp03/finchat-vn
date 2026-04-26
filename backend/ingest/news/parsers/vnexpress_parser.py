import logging
from bs4 import BeautifulSoup
from datetime import datetime
from ..models import NewsArticle

logger = logging.getLogger("vnexpress_parser")

class VnExpressParser:
    SOURCE_NAME = "VnExpress"
    
    def parse(self, url: str, html: str) -> NewsArticle:
        """Bóc tách HTML thành đối tượng NewsArticle"""
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Title
        title_tag = soup.find('h1', class_='title-detail')
        title = title_tag.text.strip() if title_tag else ""
        
        # 2. Summary (Sapo)
        summary_tag = soup.find('p', class_='description')
        summary = summary_tag.text.strip() if summary_tag else ""
        
        # 3. Content
        content_tags = soup.find_all('p', class_='Normal')
        content_paragraphs = [p.text.strip() for p in content_tags if p.text.strip()]
        content = "\n".join(content_paragraphs)
        
        # 4. Author
        author_tag = soup.find('p', class_='author_mail')
        if not author_tag:
            # Fallback for author in strong tag inside Normal p
            author_tags = soup.find_all('p', class_='Normal')
            if author_tags:
                strong_tag = author_tags[-1].find('strong')
                if strong_tag:
                    author_tag = strong_tag
        author = author_tag.text.strip() if author_tag else ""
        
        # 5. Published At
        published_at = datetime.now()
        meta_date = soup.find('meta', {'name': 'pubdate'})
        if meta_date and meta_date.get('content'):
            try:
                # Parse ISO format like: 2024-04-23T10:20:00+07:00
                published_at = datetime.fromisoformat(meta_date['content'])
            except Exception as e:
                logger.warning(f"Could not parse pubdate: {e}")
                
        # 6. Tags & Auto tagging
        tags = []
        symbols = []
        content_lower = content.lower()
        if "sjc" in content_lower:
            tags.append("sjc")
            symbols.append("SJC")
        if "nhẫn" in content_lower or "vàng nhẫn" in content_lower:
            tags.append("nhẫn")
        if "fed" in content_lower:
            tags.append("fed")
        
        # Quality check
        quality_score = 1.0
        if not title or not content:
            quality_score = 0.2
        elif not summary:
            quality_score = 0.8
            
        return NewsArticle(
            title=title,
            summary=summary,
            content=content,
            source_name=self.SOURCE_NAME,
            source_type="scrape",
            url=url,
            author=author,
            published_at=published_at,
            symbols=symbols,
            tags=tags,
            quality_score=quality_score
        )
