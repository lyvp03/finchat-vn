import logging
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from ..models import NewsArticle

logger = logging.getLogger("kitco_parser")


class KitcoParser:
    SOURCE_NAME = "Kitco"

    def parse(self, url: str, html: str) -> NewsArticle:
        """Bóc tách dữ liệu bài viết từ Kitco thông qua __NEXT_DATA__ JSON."""
        if not html:
            return None

        # Trích xuất __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            logger.warning("No __NEXT_DATA__ found for %s", url)
            return None

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.error("Failed to parse __NEXT_DATA__ JSON for %s", url)
            return None

        # Tìm node bài viết
        queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
        node = None
        for q in queries:
            qkey = q.get("queryKey", [])
            if qkey and qkey[0] == "nodeByUrlAlias":
                node = q.get("state", {}).get("data", {}).get("nodeByUrlAlias")
                break

        if not node:
            logger.warning("No article node found for %s", url)
            return None

        # 1. Title
        title = node.get("title", "")

        # 2. Summary
        summary = node.get("teaserSnippet", "")

        # 3. Content — bodyWithEmbeddedMedia là list các block HTML
        body_blocks = node.get("bodyWithEmbeddedMedia", [])
        content = self._extract_body_text(body_blocks)

        # 4. Author
        author_data = node.get("author") or {}
        author = author_data.get("name", "")

        # 5. Published At
        published_at = datetime.now()
        created_str = node.get("createdAt")
        if created_str:
            try:
                published_at = datetime.fromisoformat(created_str)
            except Exception as e:
                logger.warning("Could not parse createdAt '%s': %s", created_str, e)

        # 6. Category
        category_data = node.get("category") or {}
        category = category_data.get("name", "")

        # 7. Tags
        tags = [t.get("name", "") for t in (node.get("tags") or []) if t.get("name")]

        # 8. Auto-detect gold-related symbols
        symbols = []
        content_lower = (content + title).lower()
        if "gold" in content_lower or "xau" in content_lower:
            symbols.append("XAUUSD")
        if "silver" in content_lower:
            symbols.append("XAGUSD")

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
            category=category,
            language="en",
            region="us",
            symbols=symbols,
            tags=tags,
            quality_score=quality_score,
        )

    def _extract_body_text(self, body_blocks) -> str:
        """Trích xuất nội dung text thuần từ bodyWithEmbeddedMedia."""
        if isinstance(body_blocks, str):
            soup = BeautifulSoup(body_blocks, "html.parser")
            return soup.get_text(separator="\n", strip=True)

        if not isinstance(body_blocks, list):
            return ""

        paragraphs = []
        for block in body_blocks:
            if isinstance(block, str):
                soup = BeautifulSoup(block, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if text:
                    paragraphs.append(text)
            elif isinstance(block, dict):
                # Embedded media hoặc HTML block
                html_content = block.get("html") or block.get("body") or block.get("content") or ""
                if html_content:
                    soup = BeautifulSoup(html_content, "html.parser")
                    text = soup.get_text(separator="\n", strip=True)
                    if text:
                        paragraphs.append(text)

        return "\n".join(paragraphs)
