import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger("kitco_source")

SITEMAP_URL = "https://www.kitco.com/static-sitemaps/news.xml"


class KitcoCrawler:
    """Lấy danh sách URL bài viết từ sitemap của Kitco."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_article_urls(self, limit: int = 200) -> List[str]:
        """Lấy danh sách URL bài viết mới nhất từ sitemap Kitco (sắp xếp mới → cũ)."""
        try:
            logger.info("Fetching Kitco sitemap from %s", SITEMAP_URL)
            r = self.session.get(SITEMAP_URL, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "xml")
            url_tags = soup.find_all("url")

            # Sitemap thường sắp mới nhất ở đầu
            urls = []
            for tag in url_tags:
                loc = tag.find("loc")
                if loc and "/news/article/" in loc.text:
                    urls.append(loc.text)
                    if len(urls) >= limit:
                        break

            logger.info("Found %s article URLs from Kitco sitemap.", len(urls))
            return urls
        except Exception as e:
            logger.error("Error fetching Kitco sitemap: %s", e)
            return []

    def fetch_article_html(self, url: str) -> str:
        """Tải HTML của một bài viết Kitco."""
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as e:
            logger.error("Error fetching article %s: %s", url, e)
            return ""
