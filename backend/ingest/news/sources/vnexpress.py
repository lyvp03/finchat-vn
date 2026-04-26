import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger("vnexpress_source")

class VnExpressCrawler:
    BASE_URL = "https://vnexpress.net/chu-de/gia-vang-1403"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
    def fetch_article_urls(self, limit: int = 10) -> List[str]:
        """Lấy danh sách các URL bài viết mới nhất từ chủ đề Vàng của VnExpress có hỗ trợ phân trang"""
        urls = []
        page = 1
        
        while len(urls) < limit:
            page_url = f"{self.BASE_URL}-p{page}" if page > 1 else self.BASE_URL
            try:
                logger.info(f"Fetching URLs from {page_url}")
                response = self.session.get(page_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tin tức thường nằm trong thẻ article với class item-news
                articles = soup.find_all('article', class_='item-news')
                if not articles:
                    logger.info("No more articles found on this page.")
                    break
                    
                added_on_page = 0
                for article in articles:
                    title_tag = article.find('h2', class_='title-news') or article.find('h3', class_='title-news')
                    if title_tag:
                        a_tag = title_tag.find('a')
                        if a_tag and 'href' in a_tag.attrs:
                            href = a_tag['href']
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
                
        logger.info(f"Found {len(urls)} articles.")
        return urls
            
    def fetch_article_html(self, url: str) -> str:
        """Tải HTML của một bài viết cụ thể"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching article HTML from {url}: {e}")
            return ""
