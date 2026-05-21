import asyncio
import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime

app = FastAPI()

TICKERS = [
    "RC1CO","BYCHO","BACGO","BACHO","CAC5O","GN49O",
    "IRCPO","IRCFO","RUCDO","MGCMO","MGCOO","MGCRO",
    "PNXCO","PN43O","PLC4O","PLC5O","RAC7O","TTCAO",
    "TTCDO","TLCPO","TLCTO","TLCMO","TSC3O","TSC4O",
    "VSCTO","VSCVO","VSCXO","YMCIO","YMCJO","YMCXO",
    "YM34O","YFCJO",
]

BASE = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free"

async def fetch_ticker(client: httpx.AsyncClient, ticker: str) -> dict:
    """Fetch latest price for one ticker from BYMA open data."""
    try:
        # Try the bonds-specific endpoint first
        r = await client.get(
            f"{BASE}/bnown/seriesHistoricas/{ticker}",
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                last = data[-1]
                return {
                    "ticker": ticker,
                    "price": last.get("price") or last.get("closePrice") or last.get("last"),
                    "date":  last.get("date", ""),
                    "ok": True,
                }
    except Exception:
        pass

    # Fallback: generic quotes endpoint
    try:
        r = await client.get(
            f"{BASE}/cotizaciones/{ticker}",
            timeout=8,
        )
        if r.status_code == 200:
            d = r.json()
            price = (d.get("ultimoPrecio") or d.get("price")
                     or d.get("last") or d.get("close"))
            if price:
                return {"ticker": ticker, "price": float(price), "date": "", "ok": True}
    except Exception:
        pass

    return {"ticker": ticker, "price": None, "ok": False}


@app.get("/api/precios")
async def get_precios():
    """Return latest dirty prices for all tickers."""
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[fetch_ticker(client, tk) for tk in TICKERS]
        )
    precios = {r["ticker"]: r["price"] for r in results if r["ok"] and r["price"]}
    return {
        "precios": precios,
        "timestamp": datetime.now().isoformat(),
        "total": len(precios),
        "missing": [tk for tk in TICKERS if tk not in precios],
    }


@app.get("/api/status")
async def status():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# Serve the static HTML — must go AFTER API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
