import logging
from bs4 import BeautifulSoup
from datetime import datetime
import re
from ..models import NewsArticle

logger = logging.getLogger("cafef_parser")

class CafeFParser:
    SOURCE_NAME = "CafeF"
    
    def parse(self, url: str, html: str) -> NewsArticle:
        """Bóc tách HTML thành đối tượng NewsArticle"""
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Title
        title_tag = soup.find('h1', class_='title')
        if not title_tag:
            title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else ""
        
        # 2. Summary (Sapo)
        summary_tag = soup.find('h2', class_='sapo')
        summary = summary_tag.text.strip() if summary_tag else ""
        
        # 3. Content
        content_div = soup.find('div', class_='detail-content')
        content = ""
        if content_div:
            # Remove scripts, iframes
            for s in content_div(['script', 'iframe', 'style']):
                s.extract()
            
            content_tags = content_div.find_all(['p', 'h3', 'h2'])
            content_paragraphs = [p.text.strip() for p in content_tags if p.text.strip()]
            content = "\n".join(content_paragraphs)
        else:
            # Fallback
            paragraphs = soup.find_all('p')
            content = "\n".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 50])
            
        # 4. Author
        author_tag = soup.find('p', class_='author')
        author = author_tag.text.strip() if author_tag else ""
        
        # 5. Published At
        published_at = datetime.now()
        time_tag = soup.find('span', class_='pdate')
        if time_tag:
            # format: 18-04-2024 - 15:43 PM
            time_text = time_tag.text.strip()
            # Extract datetime using regex
            match = re.search(r'(\d{2}-\d{2}-\d{4})\s*-\s*(\d{2}:\d{2})', time_text)
            if match:
                date_str, time_str = match.groups()
                try:
                    published_at = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
                except ValueError as e:
                    logger.warning(f"Could not parse datetime {time_text}: {e}")

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
