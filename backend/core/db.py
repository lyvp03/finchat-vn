import clickhouse_connect
from core.config import settings

def get_clickhouse_client():
    """Tạo và trả về một instance của ClickHouse client (tái sử dụng connection pool)"""
    return clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        database=settings.CLICKHOUSE_DATABASE
    )

def insert_many_clickhouse(client, table: str, data: list, column_names: list, batch_size: int = 10000):
    """
    Hàm tiện ích giúp Bulk Insert dữ liệu vào ClickHouse theo từng chunk nhỏ
    Nhằm tránh quá tải và lỗi bộ nhớ khi chèn hàng triệu dòng.
    """
    if not data:
        return
        
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        client.insert(table, batch, column_names=column_names)
