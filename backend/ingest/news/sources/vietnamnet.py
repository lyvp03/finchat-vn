import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger("vietnamnet_source")


class VietnamNetCrawler:
    """Crawler cho chuyên mục Giá Vàng trên VietnamNet."""

    BASE_URL = "https://vietnamnet.vn/gia-vang-tag14642850852768478603-page{page}.html"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def fetch_article_urls(self, limit: int = 200) -> List[str]:
        """Lấy danh sách URL bài viết từ tag 'giá vàng' trên VietnamNet, hỗ trợ phân trang."""
        urls = []
        page = 1

        while len(urls) < limit:
            page_url = self.BASE_URL.format(page=page)
            try:
                logger.info(f"Fetching URLs from {page_url}")
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Bài viết nằm trong div.horizontalPost hoặc div.vnn-article-item
                articles = soup.select('div.horizontalPost, div.vnn-article-item')
                if not articles:
                    # Fallback: tìm tất cả thẻ h3 > a trong vùng content
                    articles = soup.select('.main-content h3 a, .list-content h3 a')

                if not articles:
                    logger.info(f"No more articles found on page {page}.")
                    break

                added_on_page = 0
                for article in articles:
                    # Tìm link bài viết
                    a_tag = article.find('a', href=True) if article.name != 'a' else article
                    if not a_tag or 'href' not in a_tag.attrs:
                        continue

                    href = a_tag['href']

                    # Chỉ lấy link bài viết, không lấy link chuyên mục
                    if not href or href.startswith('#') or href.startswith('javascript'):
                        continue

                    # Normalize URL
                    if href.startswith('/'):
                        href = 'https://vietnamnet.vn' + href

                    # Chỉ lấy URL vietnamnet.vn và có dạng bài viết (kết thúc bằng số + .html)
                    if 'vietnamnet.vn/' not in href:
                        continue
                    if not href.endswith('.html'):
                        continue
                    # Bỏ qua link tag/category (chứa "tag" trong URL)
                    if '-tag' in href:
                        continue

                    if href not in urls:
                        urls.append(href)
                        added_on_page += 1
                        if len(urls) >= limit:
                            break

                if added_on_page == 0:
                    logger.info("No new URLs found on this page, stopping pagination.")
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching article URLs from {page_url}: {e}")
                break

        logger.info(f"Found {len(urls)} VietnamNet articles.")
        return urls

    def fetch_article_html(self, url: str) -> str:
        """Tải HTML của một bài viết cụ thể."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching article HTML from {url}: {e}")
            return ""
