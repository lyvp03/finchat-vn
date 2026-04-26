# FinChat VN Runbook

Huong dan nay tom tat cach chay Docker, khoi tao database, chay backend va cac lenh van hanh chinh trong project.

## 1. Cau truc lien quan

- `docker-compose.yml`: chay ClickHouse container `finchat_clickhouse`.
- `backend/.env`: cau hinh ket noi ClickHouse, LLM va ChromaDB.
- `backend/api/main.py`: FastAPI app.
- `backend/db/migrations/`: SQL tao bang ClickHouse.
- `backend/jobs/worker/main.py`: worker crawl gia, crawl tin tuc, enrichment va RAG indexing theo lich.
- `frontend/`: hien tai dang trong.

## 2. Chay ClickHouse bang Docker

Chay tu thu muc root:

```powershell
cd d:\em_ly\finchat-vn
docker compose up -d
```

Kiem tra container:

```powershell
docker ps
docker logs finchat_clickhouse
```

Thong tin ket noi ClickHouse theo `docker-compose.yml`:

```text
HTTP: localhost:8123
Native: localhost:9000
Database: gold
User: phglyxg
Password: Phuongly1234
```

Dung container:

```powershell
docker compose down
```

Dung container va xoa luon volume du lieu:

```powershell
docker compose down -v
```

## 3. Khoi tao bang ClickHouse

Sau khi ClickHouse da chay, apply migration:

```powershell
Get-Content .\backend\db\migrations\001_create_gold_price.sql -Raw | docker exec -i finchat_clickhouse clickhouse-client --user phglyxg --password Phuongly1234 --database gold --multiquery

Get-Content .\backend\db\migrations\002_create_gold_news.sql -Raw | docker exec -i finchat_clickhouse clickhouse-client --user phglyxg --password Phuongly1234 --database gold --multiquery
```

Kiem tra bang:

```powershell
docker exec -it finchat_clickhouse clickhouse-client --user phglyxg --password Phuongly1234 --database gold --query "SHOW TABLES"
```

## 4. Chay backend API

Backend la FastAPI va chay truc tiep bang Python.

```powershell
cd d:\em_ly\finchat-vn\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Lenh ngan hon khi da dung trong thu muc `backend/`:

```powershell
.\venv\Scripts\uvicorn.exe api.main:app --reload
```

Hoac neu da activate venv:

```powershell
uvicorn api.main:app --reload
```

Test API:

```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/price/latest
Invoke-RestMethod "http://localhost:8000/api/news/latest?limit=5"
```

Swagger docs:

```text
http://localhost:8000/docs
```

## 5. Test chatbot

Dieu kien truoc khi test:

- ClickHouse dang chay: port `8123`.
- Ollama dang chay: port `11434`.
- Chroma da duoc index tu ClickHouse.

Kiem tra nhanh:

```powershell
Test-NetConnection 127.0.0.1 -Port 8123
Test-NetConnection 127.0.0.1 -Port 11434
```

Kiem tra Ollama model:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

Neu Ollama chua chay, mo terminal rieng:

```powershell
$env:OLLAMA_MODELS="D:\ollama_data\.ollama"
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```

Test backend goi Ollama:

```powershell
cd d:\em_ly\finchat-vn\backend
.\venv\Scripts\python.exe -c "from core.llm.factory import get_llm_client; print(get_llm_client().generate([{'role':'user','content':'Xin chao, tra loi ngan gon'}]))"
```

Test 4 scenario chatbot truc tiep:

```powershell
cd d:\em_ly\finchat-vn\backend
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -c "from chatbot.orchestrator import answer_question; tests=['Gia vang SJC hom nay?','Tin nao anh huong den vang?','Vi sao gia vang tang tuan nay?','Gia bitcoin bao nhieu?']; [print('\n---', q, '\n', (r:=answer_question(q))['intent'], '\n', r['response']) for q in tests]"
```

Test qua API:

```powershell
$body = @{ message = "Gia vang SJC hom nay?"; history = @() } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Method POST -ContentType "application/json" -Body $body
```

## 6. Chay worker

Mo terminal khac va chay:

```powershell
cd d:\em_ly\finchat-vn\backend
.\venv\Scripts\Activate.ps1
python -m jobs.worker.main
```

Neu dang dung o thu muc root `d:\em_ly\finchat-vn`, lenh `python -m jobs.worker.main` se bao loi `No module named 'jobs'` vi package `jobs` nam trong `backend/`. Co the chay theo mot trong hai cach:

```powershell
cd d:\em_ly\finchat-vn\backend
python -m jobs.worker.main
```

Hoac chay tu root bang cach set `PYTHONPATH`:

```powershell
cd d:\em_ly\finchat-vn
$env:PYTHONPATH=".\backend"
python -m jobs.worker.main
```

Worker dang ky lich:

- Gia vang: 09:00, 13:00, 17:00.
- Tin tuc: moi 30 phut.
- Enrichment: moi 1 gio.
- RAG indexing: moi 2 gio.

## 7. Crawl va xu ly du lieu thu cong

Backfill tin tuc:

```powershell
cd d:\em_ly\finchat-vn\backend
.\venv\Scripts\Activate.ps1

python -m ingest.news.services.news_backfill_service --source vnexpress --limit 300
python -m ingest.news.services.news_backfill_service --source kitco --limit 200
python -m ingest.news.services.news_backfill_service --source reuters --limit 200
```

Enrich tin tuc:

```powershell
python -m preprocessing.news_enrichment
```

Index tin tuc vao ChromaDB cho RAG:

```powershell
python -c "from rag.indexer import run_indexing; print(run_indexing(limit=1000))"
```

Sau khi backfill lai toan bo `gold_news`, nen rebuild Chroma:

```powershell
cd d:\em_ly\finchat-vn\backend
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -c "from rag.indexer import run_indexing; print(run_indexing(limit=2000))"
```

Kiem tra Chroma:

```powershell
.\venv\Scripts\python.exe -c "from rag.vector_store import GoldNewsVectorStore; s=GoldNewsVectorStore(); print(s.persist_dir); print(s.count())"
```

Hien tai Chroma persist dir dang de trong `backend/.env`:

```env
CHROMA_PERSIST_DIR=C:\Users\Admin\AppData\Local\finchat-vn\chroma_db
```

Ly do: SQLite/Chroma gap `disk I/O error` khi ghi trong workspace o o `D:`.

## 8. Chay cac script test co san

```powershell
cd d:\em_ly\finchat-vn\backend
.\venv\Scripts\Activate.ps1

python tests\test_crawl_prices.py
python tests\test_preprocess_prices.py
python tests\test_crawl_sjc.py
python tests\test_preprocess_sjc.py
```

Mot so script se ghi file ket qua vao thu muc `data/`.

## 9. Luu y cau hinh

Khi backend chay truc tiep tren may host, `backend/.env` dung:

```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=phglyxg
CLICKHOUSE_PASSWORD=Phuongly1234
CLICKHOUSE_DATABASE=gold
```

Neu sau nay dockerize backend va cho backend chay cung Docker network voi ClickHouse, doi host thanh ten service:

```env
CLICKHOUSE_HOST=clickhouse
```

Password ClickHouse hien dang nam truc tiep trong `docker-compose.yml` va `backend/.env`. Neu dua repo len Git/public repo, nen tach secret sang file `.env` rieng va khong commit.

## 10. Nen dua gi vao Docker?

Hien tai Docker chi can thiet cho ClickHouse. Cac phan co the dua vao Docker tiep:

- Backend API: nen dockerize khi muon chay on dinh, it phu thuoc terminal local.
- Worker: nen dockerize thanh service rieng, dung chung image voi backend API.
- Frontend: neu frontend phat trien tiep, co the dockerize bang Node/Nginx.

Chua nen dua vao Docker ngay:

- Ollama tren may Windows nay: nen chay native truoc vi model da nam o `D:\ollama_data\.ollama`, GPU/driver tren Windows de debug hon.
- ChromaDB: project dang dung Chroma embedded qua SQLite, khong can service rieng. Chi can mount persist dir neu dockerize backend.

Neu dockerize backend API/worker, can doi:

```env
CLICKHOUSE_HOST=clickhouse
OLLAMA_BASE_URL=http://host.docker.internal:11434
CHROMA_PERSIST_DIR=/app/chroma_db
```

`host.docker.internal` cho phep container backend goi Ollama dang chay tren Windows host.
