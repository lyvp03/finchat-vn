import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from email.utils import parsedate_to_datetime

logger = logging.getLogger("reuters_source")

GNEWS_RSS_URL = "https://news.google.com/rss/search?q={query}+site:reuters.com&hl=en-US&gl=US&ceid=US:en"


class ReutersCrawler:
    """
    Lấy tin Reuters qua Google News RSS.
    Reuters chặn scraping trực tiếp (Cloudflare/DataDome),
    nên dùng Google News RSS làm nguồn metadata.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def fetch_article_urls(self, limit: int = 200) -> List[str]:
        """Trả về danh sách Google News link IDs."""
        all_items = self._fetch_rss_items(limit)
        return [item["link"] for item in all_items]

    def fetch_article_html(self, url: str) -> str:
        """Không cần fetch HTML. Trả về URL gốc (parser sẽ tìm trong cache RSS)."""
        return url

    def fetch_rss_items(self, limit: int = 200) -> List[Dict]:
        """Public API: trả về danh sách metadata bài viết từ RSS."""
        return self._fetch_rss_items(limit)

    def _fetch_rss_items(self, limit: int) -> List[Dict]:
        """Fetch RSS items từ nhiều query Google News."""
        queries = ["gold price", "gold market precious metals", "gold futures commodity"]
        all_items = []
        seen_titles = set()

        for query in queries:
            if len(all_items) >= limit:
                break

            url = GNEWS_RSS_URL.format(query=query.replace(" ", "+"))
            logger.info("Fetching Reuters via Google News RSS: query='%s'", query)

            try:
                r = self.session.get(url, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "xml")

                for item in soup.find_all("item"):
                    if len(all_items) >= limit:
                        break

                    title_tag = item.find("title")
                    title = title_tag.text.strip() if title_tag else ""

                    # Loại bỏ " - Reuters" ở cuối title
                    if title.endswith(" - Reuters"):
                        title = title[:-len(" - Reuters")].strip()

                    # Bỏ qua trùng lặp theo title
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)

                    link_tag = item.find("link")
                    link = link_tag.text.strip() if link_tag else ""

                    pub_tag = item.find("pubDate")
                    pub_date = None
                    if pub_tag and pub_tag.text:
                        try:
                            pub_date = parsedate_to_datetime(pub_tag.text)
                        except Exception:
                            pass

                    all_items.append({
                        "title": title,
                        "link": link,
                        "published_at": pub_date,
                    })

            except Exception as e:
                logger.error("Error fetching RSS for query '%s': %s", query, e)

        logger.info("Found %s Reuters article items via Google News RSS.", len(all_items))
        return all_items
