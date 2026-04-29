import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger("cafef_source")

class CafeFCrawler:
    BASE_URL = "https://cafef.vn/gia-vang.html"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
    def fetch_article_urls(self, limit: int = 10) -> List[str]:
        """Lấy danh sách các URL bài viết mới nhất từ thẻ 'gia-vang' của CafeF có hỗ trợ phân trang"""
        urls = []
        page = 1
        
        while len(urls) < limit:
            page_url = f"https://cafef.vn/gia-vang/trang-{page}.html" if page > 1 else self.BASE_URL
            try:
                logger.info(f"Fetching URLs from {page_url}")
                response = self.session.get(page_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                links = soup.find_all('a', href=True)
                if not links:
                    logger.info("No more articles found on this page.")
                    break
                    
                added_on_page = 0
                for a in links:
                    href = a['href']
                    if '.chn' in href and ('gia-vang' in href or 'vang' in href):
                        if href.startswith('/'):
                            href = 'https://cafef.vn' + href
                        
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
