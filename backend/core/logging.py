import logging
import sys
from core.config import settings

def setup_logger(name: str) -> logging.Logger:
    """Thiết lập logger chuẩn cho toàn bộ ứng dụng."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Ngăn chặn log bị nhân đôi khi propagate lên root logger
        logger.propagate = False
        
    return logger
