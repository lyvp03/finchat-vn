# Oracle Cloud Deploy Guide + Backend Config Checklist

## 0. Mục tiêu

Tài liệu này hướng dẫn đưa backend gold RAG/chatbot lên Oracle Cloud Free Tier để:

- Chạy backend 24/7 mà không cần treo laptop.
- Chạy scheduler/crawler tự động.
- Lưu dữ liệu vào ClickHouse.
- Lưu vector/chunk vào Qdrant.
- Gọi LLM cloud thay vì chạy Ollama local trên máy cá nhân.

Kiến trúc hiện tại:

```text
Oracle VM (VPS)
├── FastAPI API service (app backend)
├── Scheduler worker service (chạy crawlers, preprocess)
├── ClickHouse (lưu gold_price, market_price, gold_news)
└── Docker volumes

External Cloud Services
├── Qdrant Cloud (lưu vector/chunk cho RAG)
└── Ollama Cloud / Gemini / OpenAI-compatible API
```

---

## 1. Vì sao dùng Oracle Cloud cho project này?

Oracle Cloud Free Tier có nhóm Always Free phù hợp để chạy một VPS nhỏ 24/7. Với project hiện tại, Oracle nên dùng để chạy backend, database, Qdrant và scheduler. Không nên chạy local LLM nặng trên Oracle Free vì VM free không có GPU.

Nên dùng:

```text
Oracle Cloud:
- FastAPI API
- Scheduler worker (VnExpress, Kitco, CafeF, Market Data)
- ClickHouse DB
- Preprocessing (FinBERT, XLM-Roberta sentiment)

Cloud Services:
- Qdrant Cloud (Vector DB)
- Ollama Cloud / Gemini / OpenAI API
```

Không nên dùng:

```text
Oracle Cloud Free:
- Ollama local model 7B/14B nặng
- training model
- batch sentiment quá lớn nếu không kiểm soát RAM
```

---

## 2. Oracle VM nên chọn

Khuyến nghị:

```text
Image: Ubuntu 22.04 hoặc Ubuntu 24.04
Shape: VM.Standard.A1.Flex
CPU: 2–4 OCPU
RAM: 12–24 GB
Boot volume: 100–200 GB
Architecture: ARM64
```

Lưu ý:

- A1.Flex là ARM, nên Docker image cần hỗ trợ `linux/arm64`.
- Quá trình Preprocessing/Enrichment hiện tải 2 model NLP (FinBERT và XLM-Roberta) tốn khoảng 2-3 GB RAM, nên VM phải có tối thiểu 6-12GB RAM.
- ClickHouse có image ARM64, chạy rất nhẹ.
- Nếu bị báo hết capacity khi tạo VM ARM, hãy tạo VM AMD Standard E2.1 Micro (RAM 1GB), tuy nhiên sẽ không đủ RAM để chạy local sentiment models (phải tắt job preprocess).

---

## 3. Cấu trúc service khuyến nghị

Không nên để APScheduler chạy chung trong API process nếu sau này API scale nhiều worker. Tốt nhất tách `api` và `scheduler` thành 2 container.

```text
services:
  api        -> nhận request /api/chat, /api/health
  scheduler  -> chạy crawl/preprocess/index theo lịch
  clickhouse -> structured price/news/market data

external:
  Qdrant Cloud -> vector store cho news chunks (không chạy container)
```

Lợi ích:

- API restart không làm duplicate job.
- Scheduler restart độc lập.
- Tránh lỗi APScheduler chạy nhiều lần nếu `uvicorn --workers > 1`.
- Dễ debug log từng phần.

---

## 4. Docker Compose mẫu

Tạo file `docker-compose.prod.yml`:

Xem file thực tế: `docker-compose.prod.yml` trong repo.

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: finchat-api
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
    env_file:
      - backend/.env.prod
    ports:
      - "8000:8000"
    depends_on:
      - clickhouse
    restart: unless-stopped

  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: finchat-worker
    command: python -m jobs.worker.main
    env_file:
      - backend/.env.prod
    depends_on:
      - clickhouse
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: finchat-clickhouse
    ports:
      - "127.0.0.1:8123:8123"
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    environment:
      CLICKHOUSE_DB: gold
      CLICKHOUSE_USER: ${CLICKHOUSE_USER:-phglyxg}
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD}
    ulimits:
      nofile:
        soft: 262144
        hard: 262144
    restart: unless-stopped

volumes:
  clickhouse_data:
```

Lưu ý:
- ClickHouse chỉ bind `127.0.0.1` — không expose ra Internet.
- Qdrant là external cloud, không cần container.

Nếu không cần public ClickHouse, sau khi test xong nên bỏ port public `8123` và `9000`, hoặc chỉ expose nội bộ bằng Docker network.

---

## 5. `.env.prod` mẫu

Tạo file `backend/.env.prod` trên server. Không commit file này lên GitHub.

Xem mẫu: `backend/.env.prod.example` trong repo.

**Chỉ khai báo các biến mà `core/config.py` thực sự đọc:**

```env
# ClickHouse — dùng service name 'clickhouse' trong Docker Compose
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=gold
CLICKHOUSE_USER=phglyxg
CLICKHOUSE_PASSWORD=your_strong_password

# Qdrant Cloud
QDRANT_URL=https://your-cluster-id.region.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=gold_news_chunks
QDRANT_TIMEOUT_SECONDS=30
QDRANT_UPSERT_BATCH_SIZE=64

# LLM — dùng Ollama Cloud hoặc Gemini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=your_ollama_api_key
LLM_MODEL=qwen2.5:7b
LLM_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=120

# Embedding — vector dimension tự detect từ model, không cần khai báo
EMBEDDING_MODEL=all-MiniLM-L6-v2

# RAG
RAG_TOP_K=8
RAG_CANDIDATE_K=24
RAG_CONTEXT_TOP_N=3
RAG_CONTEXT_MAX_CHARS=500

# Application
LOG_LEVEL=INFO
```

> **Lưu ý:** Scheduler cron/interval hiện hardcode trong `jobs/worker/main.py`.
> Nếu muốn config qua env, cần sửa worker đọc biến môi trường.

---

## 6. Config rất hay bị sai khi chuyển từ local sang Docker/Oracle

### 6.1. Không dùng `localhost` giữa các container

Sai:

```env
CLICKHOUSE_HOST=localhost
```

Đúng trong Docker Compose:

```env
CLICKHOUSE_HOST=clickhouse
```

`localhost` bên trong container API là chính container API, không phải container ClickHouse.

Riêng Qdrant: dùng URL cloud trực tiếp, không phải Docker service name:

```env
QDRANT_URL=https://your-cluster-id.region.aws.cloud.qdrant.io
```

---

### 6.2. LLM cloud không được gọi `localhost:11434`

Sai:

```env
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
```

Đúng nếu dùng Ollama Cloud:

```env
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=your_key
LLM_MODEL=qwen2.5:7b
```

LLM client tự gửi header `Authorization: Bearer <key>` khi có `OLLAMA_API_KEY`.

---

### 6.3. Không chạy nhiều scheduler cùng lúc

Nếu scheduler nằm trong FastAPI startup và bạn chạy:

```bash
uvicorn app.main:app --workers 4
```

job có thể chạy 4 lần.

MVP nên dùng:

```bash
uvicorn app.main:app --workers 1
```

Tốt hơn:

```text
api container: chỉ serve API
scheduler container: chỉ chạy job
```

---

### 6.4. Qdrant vector size tự detect — không cần hardcode

Code hiện tại gọi `embedder.dimension()` để tự lấy số chiều từ model:

```python
# qdrant_store.py — ensure_collection()
VectorParams(size=self.embedder.dimension(), ...)
```

Vì vậy **không cần** khai báo `QDRANT_VECTOR_SIZE` trong env.

Nếu đổi embedding model (ví dụ `all-MiniLM-L6-v2` → `bge-m3`), cần:

- Xóa/recreate Qdrant collection (vector size thay đổi), hoặc
- Đổi tên collection mới: `QDRANT_COLLECTION=gold_news_chunks_bge_m3`
- Re-index toàn bộ bài viết.

---

### 6.5. Không index lại toàn bộ nếu không cần

Nên tracking:

```text
indexed_at
embedding_model
chunking_version
vector_store
```

Khi scheduler chạy, chỉ index bài:

```text
is_relevant = true
is_duplicate = false
indexed_at IS NULL
```

---

## 7. Backend config — cấu trúc hiện tại

Config nằm tại `backend/core/config.py`, dùng `os.getenv()` trực tiếp:

```python
import os
from dotenv import load_dotenv

class Settings:
    # ClickHouse
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "gold")

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

    # Qdrant Cloud
    QDRANT_URL = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "gold_news_chunks")

    # Embedding — vector dimension auto-detected
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # RAG
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "8"))
    RAG_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "24"))
    RAG_CONTEXT_TOP_N = int(os.getenv("RAG_CONTEXT_TOP_N", "3"))
    RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "500"))

settings = Settings()
```

Chỉ `.env.prod` khai báo những biến nằm trong class này — không thêm biến "phantom" mà code không đọc.

---

## 8. RAG config nên ưu tiên cho chất lượng answer

Hiện chatbot của bạn đã có price + XAUUSD + USDVND + premium. Vì vậy answer nên ưu tiên evidence theo thứ tự:

```text
1. Domestic price
2. XAUUSD
3. USDVND
4. Premium
5. Direct news
6. Contextual news
7. Weak news
```

Rule khuyến nghị hiện tại của hệ thống:

```text
- Tự động phân loại qua hàm classify_news_tier:
  - direct: Tiêu đề nhắc trực tiếp biến động giá vàng
  - contextual: Nhắc đến thị trường vàng hoặc vĩ mô
  - weak: Các tin yếu khác, không dùng để giải thích nguyên nhân
```

Cơ chế Evidence Grader sẽ đánh giá độ tin cậy của dữ liệu:

```text
- Đủ 4 nguồn (price, market, premium, direct news) -> High confidence
- Có market data nhưng thiếu direct news -> Medium confidence (dùng ngôn từ dự phòng)
- Thiếu cả market và news -> Low/Insufficient confidence
```

---

## 9. Evidence grader config

Nên tách correlation và news causality.

Output mong muốn:

```json
{
  "can_explain_market_correlation": true,
  "can_explain_news_cause": false,
  "confidence": "medium",
  "primary_driver_type": "market_correlation",
  "available_data": ["domestic_price", "xauusd", "usd_vnd", "premium"],
  "weak_context": ["contextual_news"],
  "missing_data": ["direct_news"]
}
```

Prompt synthesis tự động nhận metadata grading để quyết định ngôn ngữ khẳng định hay phòng ngừa (hedging).

Ví dụ:

```text
"Sự suy giảm này có thể liên quan đến đà giảm của XAUUSD trên thị trường quốc tế, tuy nhiên chưa có tin tức trực tiếp xác nhận..."
```

---

## 10. Time range config

Một lỗi hay gặp là price dùng một khoảng thời gian, market/news dùng khoảng khác.

Khuyến nghị:

```text
resolve_time_range() chạy một lần ở đầu request
sau đó truyền cùng time_range cho:
- price query
- market query
- premium calculation
- news retrieval
```

Nếu user không nói thời gian:

```text
Dùng rolling 7 ngày theo latest price timestamp
```

Không nên dùng ngày hiện tại của server nếu dữ liệu price mới nhất cũ hơn.

Config:

```env
DEFAULT_ROLLING_DAYS=7
USE_PRICE_LATEST_TS_AS_REFERENCE=true
```

---

## 11. Các bước deploy Oracle chi tiết

### Bước 1: Tạo VM

Trên Oracle Cloud Console:

```text
Compute -> Instances -> Create instance
```

Chọn:

```text
Image: Ubuntu 22.04/24.04
Shape: VM.Standard.A1.Flex
OCPU/RAM: 2 OCPU + 12 GB RAM hoặc 4 OCPU + 24 GB RAM
Boot volume: 100–200 GB
SSH key: upload public key hoặc generate key
```

### Bước 2: Mở port

Trong VCN/Security List hoặc Network Security Group, mở:

```text
22/tcp    SSH
8000/tcp  FastAPI API
80/tcp    nếu dùng Nginx HTTP
443/tcp   nếu dùng HTTPS
```

Không nên public:

```text
8123 ClickHouse
9000 ClickHouse native
```

Trừ khi bạn biết rõ đang làm gì và có auth/firewall.

### Bước 3: SSH vào VM

```bash
ssh -i ~/.ssh/oracle_key ubuntu@<PUBLIC_IP>
```

### Bước 4: Cài Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Logout rồi login lại, sau đó test:

```bash
docker --version
docker compose version
```

### Bước 5: Clone project

```bash
git clone <your_repo_url>
cd <your_project>
```

### Bước 6: Tạo `.env.prod`

```bash
cp backend/.env.prod.example backend/.env.prod
nano backend/.env.prod
```

Sửa các giá trị thực tế, chú ý:

```env
CLICKHOUSE_HOST=clickhouse
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=...
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_API_KEY=...
```

### Bước 7: Chạy Docker Compose

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Kiểm tra container:

```bash
docker ps
```

Xem log:

```bash
docker logs -f finchat-api

docker logs -f finchat-worker
```

### Bước 8: Test API

Trên server:

```bash
curl http://localhost:8000/api/health
```

Từ máy cá nhân:

```bash
curl http://<PUBLIC_IP>:8000/api/health
```

Test chat:

```bash
curl -X POST "http://<PUBLIC_IP>:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Vì sao giá vàng SJC giảm?",
    "history": []
  }'
```

---

## 12. Firewall trên Ubuntu

Nếu dùng `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8000/tcp
sudo ufw enable
sudo ufw status
```

Nếu dùng Nginx/HTTPS sau này:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## 13. Nginx reverse proxy tùy chọn

Nếu muốn dùng domain thay vì `IP:8000`, cài Nginx:

```bash
sudo apt install -y nginx
```

Config mẫu:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 14. Backup dữ liệu

Dữ liệu quan trọng nằm trong Docker volumes:

```text
clickhouse_data
```
(Vector DB đã an toàn trên Qdrant Cloud)

Backup đơn giản:

```bash
mkdir -p ~/backups

docker run --rm \
  -v clickhouse_data:/data \
  -v ~/backups:/backup \
  ubuntu tar czf /backup/clickhouse_data_$(date +%F).tar.gz /data
```

Nên backup trước khi:

```text
- đổi schema lớn
- recreate Qdrant collection
- update Docker image
- migrate server
```

---

## 15. Logs và monitoring tối thiểu

Các lệnh hay dùng:

```bash
docker ps

docker logs --tail 100 finchat-api

docker logs --tail 100 finchat-worker

docker stats

df -h

free -h
```

Nên log mỗi job:

```text
job_name
started_at
finished_at
status
records_fetched
records_inserted
records_updated
records_indexed
error_message
```

Có thể lưu vào bảng `job_runs` trong ClickHouse.

---

## 16. Checklist trước khi coi deploy là ổn

```text
[ ] API /health OK
[ ] /api/chat OK
[ ] ClickHouse container chạy ổn
[ ] Worker container chạy ổn
[ ] Crawl price chạy thành công
[ ] Crawl XAUUSD, USDVND (Market) chạy thành công
[ ] Crawl news (VnExpress, Kitco, CafeF) chạy thành công
[ ] Preprocess news chạy thành công (RAM không bị tràn)
[ ] Qdrant index đẩy lên Cloud thành công
[ ] Restart container không mất data ClickHouse
[ ] Cấu hình API key Qdrant và Ollama Cloud chính xác
[ ] Hệ thống Evidence Grader hoạt động tốt (trả về JSON sources đầy đủ)
```

---

## 17. Thứ tự triển khai khuyến nghị

```text
Phase 1: Deploy infrastructure
- Oracle VM
- Docker
- docker-compose.prod.yml
- .env.prod
- ClickHouse + Qdrant + API chạy được

Phase 2: Deploy scheduler
- scheduler container
- crawl price
- crawl market
- crawl news
- preprocess/index

Phase 3: Stabilize RAG answer
- evidence grader
- time range sync
- news direct/contextual/weak
- compact context

Phase 4: Hardening
- Nginx + domain
- HTTPS
- backup
- job_runs table
- basic alert/logging
```

---

## 18. Quick commands summary

```bash
# SSH
ssh -i ~/.ssh/oracle_key ubuntu@<PUBLIC_IP>

# Pull latest code
git pull

# Start/rebuild
docker compose -f docker-compose.prod.yml up -d --build

# Stop
docker compose -f docker-compose.prod.yml down

# Logs
docker logs -f finchat-api
docker logs -f finchat-worker

# Check containers
docker ps

# Resource usage
docker stats

# Test API
curl http://localhost:8000/health
```

---

## 19. Notes riêng cho project gold RAG

### 19.1. Backend nên dùng evidence theo thứ tự

```text
domestic_price -> xauusd -> usdvnd -> premium -> direct_news -> contextual_news
```

### 19.2. Câu hỏi nguyên nhân không nên chỉ dựa vào news

Nếu hỏi:

```text
Vì sao giá vàng SJC giảm?
```

Answer tốt nên ưu tiên:

```text
- SJC giảm bao nhiêu
- XAUUSD có giảm không
- USDVND có biến động không
- premium đang cao/thấp ra sao
- có direct news không
```

### 19.3. News score thấp không dùng làm nguyên nhân

Nếu news score = 0.35, chỉ nên nói:

```text
Tin này liên quan yếu đến bối cảnh thị trường, không đủ cơ sở để giải thích nguyên nhân giá giảm.
```

---

## 20. Kết luận

Khi backend đã xong, Oracle Cloud Free Tier có thể dùng để chạy MVP mà không cần treo laptop. Cấu hình hợp lý nhất là:

```text
Oracle VM:
- FastAPI API
- Scheduler worker
- ClickHouse

External provider:
- Qdrant Cloud (Vector DB)
- Ollama Cloud / Gemini / OpenAI-compatible LLM
```

Điểm cần chú ý nhất khi chuyển sang Oracle:

```text
1. Đảm bảo model sentiment có đủ RAM để chạy trên VM (tối thiểu 6GB).
2. Tách Scheduler Worker thành container riêng biệt.
3. Không expose port ClickHouse ra Internet nếu không cần thiết.
4. Đảm bảo cấu hình URL Cloud Qdrant và API Key.
```
