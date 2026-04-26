from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, gold_news, gold_price, health

app = FastAPI(title="FinChat VN API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(gold_price.router)
app.include_router(gold_news.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"name": "FinChat VN API", "status": "ok"}
