from fastapi import APIRouter, HTTPException, Query

from tools.price_tool import get_latest_price, get_price_analysis
from core.db import get_clickhouse_client
from ingest.price.repositories.gold_price_repository import GoldPriceRepository

router = APIRouter(prefix="/api/price", tags=["gold_price"])

@router.get("/timeseries")
def price_timeseries(type_code: str = Query(default="SJL1L10", alias="type"), days: int = 30):
    repo = GoldPriceRepository(get_clickhouse_client())
    records = repo.get_timeseries(type_code=type_code, days=days)
    return {"ok": True, "type_code": type_code, "days": days, "data": records}


@router.get("/latest")
def latest_price(type_code: str | None = Query(default=None, alias="type")):
    result = get_latest_price(type_code=type_code)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/history")
def price_history(type_code: str = Query(default="SJL1L10", alias="type"), days: int = 30):
    result = get_price_analysis(type_code=type_code, days=days)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result
