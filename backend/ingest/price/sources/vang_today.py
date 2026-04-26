import logging
import requests
from typing import List

logger = logging.getLogger("vang_today_source")

API_BASE = "https://www.vang.today/api/prices"


class VangTodayCrawler:
    """Lấy dữ liệu JSON thô từ API vang.today"""

    def __init__(self):
        self.session = requests.Session()

    def fetch_raw(self, type_code: str, days: int = 1) -> dict:
        """Gọi API và trả về payload JSON gốc."""
        logger.info("Fetching prices for type=%s days=%s", type_code, days)
        try:
            r = self.session.get(
                API_BASE, params={"type": type_code, "days": days}, timeout=30
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("Error fetching prices for type=%s: %s", type_code, e)
            return {}
