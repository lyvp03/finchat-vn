# Kế hoạch Triển khai: Chatbot Cố vấn Giá Vàng Việt Nam

Kế hoạch này phác thảo cách thức xây dựng một dự án tương tự **Crypto Chatbot** hiện tại nhưng áp dụng cho **Giá Vàng Việt Nam** (SJC, DOJI, PNJ...) và sử dụng **Python (FastAPI)** cho toàn bộ Backend thay vì NestJS.

## Quyết định Kỹ Thuật (Đã chốt)

> [!NOTE]
> **Tổng hợp các quyết định từ User**:
> - **Phạm vi Vàng:** Lấy 6 loại vàng trên API, bao gồm cả vàng quốc tế (Dữ liệu vàng quốc tế sẽ được dùng làm context cho LLM suy luận sự biến động và chênh lệch).
> - **Real-time vs Polling:** Sử dụng phương pháp Hybrid: API Polling cho Biểu đồ giá vàng (do giá vàng VN ít biến động liên tục), và Streaming (via Redis) cho Chatbot UI.
> - **Sentiment NLP:** Sử dụng trực tiếp mô hình **PhoBERT** trên Worker để đánh giá cảm xúc tin tức (chấp nhận tốn thêm RAM/VRAM).
> - **Kiến trúc Tool Calling:** Sẽ quyết định sau ở Giai đoạn Implement API (sử dụng HTTP hay gọi function trực tiếp).

---

## 1. Kiến trúc Tổng thể (Architecture)

Kiến trúc sẽ được thiết kế bám sát nguyên lý của dự án Crypto Chatbot cũ, bao gồm 2 service chính chạy song song: **App Service (API)** và **Worker Service (Cronjob)**, kết hợp với Redis để khóa phân tán (Distributed Lock) và ClickHouse/PostgreSQL để lưu trữ.

### 1.1 Khác biệt & Tương đồng so với dự án cũ (Crypto Chatbot)
| Thành phần | Tiền ảo (Dự án cũ) | Giá Vàng VN (Dự án Mới) |
| :--- | :--- | :--- |
| **Backend Core** | NestJS (TypeScript) | **FastAPI (Python)** |
| **Worker Service** | `@nestjs/schedule` (Cron) + Redis | **APScheduler** (hoặc Celery) + Redis |
| **Mã nguồn Data** | API Binance / CoinDesk | Web Scraping (SJC, DOJI, CafeF...) API |
| **Chatbot Tools** | `getKlines`, `getNewsLimit`, `getTimeNow` | `get_gold_prices`, `get_gold_news`, `get_time_now` (Sử dụng Vector Search) |
| **Database** | ClickHouse | Time-Series: PostgreSQL/ClickHouse <br> Vector DB: Qdrant / ChromaDB |

### 1.2 Các Layer Cốt lõi
1. **Worker Service:** Tiến trình chạy ngầm định kỳ (Cron). Thu thập dữ liệu (đồng bộ giá vàng và tin tức thị trường), sử dụng Redis Lock để tránh đụng độ giữa các worker.
2. **Data Pipeline & ML:** Làm sạch dữ liệu, đưa tin tức qua model NLP tiếng Việt (PhoBERT) để đánh giá Sentiment (Tích cực/Tiêu cực đối với giá vàng) trước khi lưu.
3. **App Service (API):** Cung cấp API truy xuất giá vàng (Polling), tin tức và API Chatbot (Streaming qua Redis). Hỗ trợ gọi OpenAI kèm function calling/tools tương tự như `chat-bot.service.ts`.
4. **Frontend Interface (React/Vite):** Tái sử dụng giao diện cũ. Sử dụng Polling để vẽ biểu đồ và SSE/Websocket để render tin nhắn Chatbot mượt mà.

---

## 2. Chi tiết Triển khai (Proposed Changes)

### 2.1 Worker Service (Data Synchronization)

Tương tự như `worker-sync-binance.service.ts` và `worker-sync-news.service.ts`, chúng ta sẽ có các worker độc lập chạy bằng APScheduler trong FastAPI:

- **Đồng bộ Giá Vàng (`worker_sync_gold_price.py`):**
  - Cào dữ liệu từ các trang uy tín (ví dụ: `sjc.com.vn`, `giavang.net`).
  - *Tần suất:* Chạy Job mỗi 15 - 30 phút một lần (vì giá vàng vật chất ít khi biến động theo từng giây, thay vì 5 phút như Crypto).
  - *Locking:* Sử dụng Redis Lock (`is_locking_sync_gold`) để đảm bảo chỉ có 1 tiến trình crawl chạy tại một thời điểm.
  - *Dữ liệu lưu:* `(Thời_gian, Thương_hiệu, Loại_vàng, Giá_mua, Giá_bán)`.

- **Đồng bộ Tin tức (`worker_sync_gold_news.py`):**
  - Cào qua RSS hoặc BeautifulSoup từ CafeF, VnExpress, Dân Trí.
  - Chạy tin tức qua model NLP để đánh giá Sentiment (Positive/Negative) và chấm điểm đối với vàng.
  - *Tần suất:* Chạy Job mỗi 1 - 2 giờ.

### 2.2 Database (Lưu trữ Phân tách)
- **Time-Series DB (ClickHouse / PostgreSQL):** 
  - Bảng `gold_price`: `(timestamp, brand, type, buy_price, sell_price)`.
- **Vector DB (Qdrant / ChromaDB):**
  - Collection `gold_news`: Lưu trữ nội dung tin tức, vector embedding và metadata (sentiment, publishedOn). Phục vụ cho Semantic Search (RAG).

### 2.3 Backend API (FastAPI App Service)

Cấu trúc thư mục của API sẽ tương tự `src/modules` của NestJS:

#### [NEW] `backend/app/main.py`
Entrypoint của FastAPI app (tương đương `main.ts`). Khởi tạo cấu hình, middlewares (CORS), và Swagger UI.

#### [NEW] `backend/app/routers/price.py`
API cung cấp dữ liệu giá vàng lịch sử để vẽ biểu đồ và cho Agent sử dụng (Tương đương router `kline`). Có hỗ trợ khoảng thời gian `fromTime`, `toTime`, `interval`.

#### [NEW] `backend/app/routers/news.py`
API lấy tin tức đã đánh giá Sentiment (Tương đương router `news`). Hỗ trợ pagination/limit.

#### [NEW] `backend/app/services/chatbot_service.py`
Service xử lý Logic Chatbot (Bản sao cấu trúc của `chat-bot.service.ts` nhưng viết bằng Python).
- Tích hợp `OpenAI API`.
- **System Prompt:** Điều chỉnh tư duy của bot tập trung vào đặc điểm của Vàng Việt Nam (chênh lệch mua bán lớn, không dự đoán giá, trả lời trung lập dựa trên dữ liệu, vv).
- **Function Calling (Tools):**
  - `get_gold_prices`: Lấy dữ liệu giá vàng (mua/bán) trong một khoảng thời gian.
  - `get_gold_news`: Lấy các tin tức vĩ mô/thị trường ảnh hưởng đến giá vàng.
  - `get_time_now`: Lấy timestamp hiện tại để chatbot tự suy luận ra `fromTime`, `toTime` khi có câu hỏi tương đối (ví dụ: "giá hôm nay", "tuần trước").
- Khi chatbot quyết định dùng tools, FastAPI sẽ gọi các hàm nội bộ (hoặc gọi HTTP nội bộ) tương tự như logic của NestJS.

### 2.4 Frontend (React/Vite)
Tận dụng lại phần lớn UI của dự án `crypto-chatbot` cũ, chỉ cần thay đổi:
- **Biểu đồ:** Thay vì biểu đồ nến (OHLCV) của Crypto, cần vẽ Line Chart hoặc Area Chart so sánh **Giá Mua** và **Giá Bán** (Spread) vì Vàng vật chất ở VN quan trọng nhất là chênh lệch mua/bán.
- **Bộ lọc:** Thêm dropdown lọc thương hiệu (SJC, PNJ, DOJI).
- **Chat UI:** Không thay đổi nhiều, tiếp tục hiển thị tin nhắn và các trích dẫn tin tức.

---

## 3. Lộ trình Thực hiện (Roadmap)

- **Giai đoạn 1 (Data & DB):** Xây dựng các script Worker lấy dữ liệu giá vàng và tin tức thị trường Việt Nam bằng Python. Setup Database và Redis.
- **Giai đoạn 2 (Backend Core & ML):** Dựng FastAPI server (routers cho Price và News), tích hợp mô hình đánh giá sentiment.
- **Giai đoạn 3 (Chatbot Integration):** Xây dựng `chatbot_service.py` với System Prompt mới và cấu hình Tool calls giống hệ thống cũ.
- **Giai đoạn 4 (Frontend):** Kết nối React frontend tới FastAPI backend và tuỳ chỉnh biểu đồ cho phù hợp với đặc thù Vàng.

---

## 4. Quyết định Kỹ Thuật (Đã Chốt)

- **Đồng bộ Frontend & Backend:** Dùng **API Polling** định kỳ để lấy giá vàng, tối ưu tài nguyên server do tần suất cập nhật giá vàng thấp.
- **Trải nghiệm Chatbot:** Dùng **Redis Pub/Sub (Websocket/SSE)** để làm luồng truyền tải chữ (Streaming) cho Chatbot tương tự ChatGPT.
- **Mô hình NLP:** Chạy trực tiếp **PhoBERT** trong Worker process để phân tích cảm xúc tin tức.
