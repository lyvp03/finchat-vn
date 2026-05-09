import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime
from ..models import NewsArticle

logger = logging.getLogger("vietnamnet_parser")


class VietnamNetParser:
    SOURCE_NAME = "VietnamNet"

    def parse(self, url: str, html: str) -> NewsArticle:
        """Bóc tách HTML thành đối tượng NewsArticle."""
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # 1. Title
        title_tag = soup.find('h1', class_='content-detail-title')
        if not title_tag:
            title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else ""

        # 2. Summary (Sapo)
        summary_tag = soup.find('h2', class_='content-detail-sapo')
        if not summary_tag:
            summary_tag = soup.find('div', class_='content-detail-sapo')
        summary = summary_tag.text.strip() if summary_tag else ""

        # 3. Content
        content = ""
        content_div = soup.find('div', class_='maincontent')
        if not content_div:
            content_div = soup.find('div', class_='content-detail-main')
        if not content_div:
            content_div = soup.find('div', id='maincontent')

        if content_div:
            # Remove scripts, iframes, ads
            for tag in content_div(['script', 'iframe', 'style', 'ins', 'figure']):
                tag.extract()
            # Remove related articles / đọc thêm
            for related in content_div.find_all('div', class_=re.compile(r'(insert-ads|box-relatednews|article-relate|VCSortableIn498)')):
                related.extract()

            content_tags = content_div.find_all(['p', 'h2', 'h3'])
            content_paragraphs = [p.get_text(strip=True) for p in content_tags if p.get_text(strip=True)]
            content = "\n".join(content_paragraphs)

        # Fallback nếu content vẫn rỗng
        if not content:
            paragraphs = soup.find_all('p')
            content = "\n".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 50])

        # 4. Author
        author = ""
        author_div = soup.find('div', class_='article-detail-author')
        if author_div:
            name_tag = author_div.find('a') or author_div.find('span', class_='name')
            author = name_tag.text.strip() if name_tag else author_div.text.strip()

        if not author:
            # Fallback: tìm trong p.author hoặc strong cuối bài
            author_p = soup.find('p', class_='author')
            if author_p:
                author = author_p.text.strip()

        # 5. Published At
        published_at = datetime.now()

        # Cách 1: meta tag article:published_time
        meta_date = soup.find('meta', property='article:published_time')
        if not meta_date:
            meta_date = soup.find('meta', {'name': 'pubdate'})

        if meta_date and meta_date.get('content'):
            try:
                published_at = datetime.fromisoformat(meta_date['content'])
            except Exception:
                pass
        else:
            # Cách 2: Tìm trong breadcrumb time element
            time_tag = soup.find('div', class_='bread-crumb-detail__time')
            if not time_tag:
                time_tag = soup.find('span', class_='bread-crumb-detail__time')
            if time_tag:
                time_text = time_tag.text.strip()
                # Format: "Thứ Bảy, 02/05/2026 - 09:40"
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}:\d{2})', time_text)
                if match:
                    date_str, time_str = match.groups()
                    try:
                        published_at = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
                    except ValueError as e:
                        logger.warning(f"Could not parse datetime '{time_text}': {e}")

        # 6. Tags & Auto tagging
        tags = []
        symbols = []
        content_lower = (content + " " + title).lower()
        if "sjc" in content_lower:
            tags.append("sjc")
            symbols.append("SJC")
        if "nhẫn" in content_lower or "vàng nhẫn" in content_lower:
            tags.append("nhẫn")
        if "fed" in content_lower or "cục dự trữ liên bang" in content_lower:
            tags.append("fed")
        if "doji" in content_lower:
            tags.append("doji")
            symbols.append("DOJI")
        if "pnj" in content_lower:
            tags.append("pnj")
        if "lạm phát" in content_lower:
            tags.append("inflation")

        # Quality check
        quality_score = 1.0
        if not title or not content:
            quality_score = 0.2
        elif not summary:
            quality_score = 0.8
        elif len(content) < 100:
            quality_score = 0.5

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
            quality_score=quality_score,
        )
