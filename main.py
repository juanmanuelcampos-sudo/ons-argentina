import asyncio
import time
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from datetime import datetime

app = FastAPI()

# ── IOL token cache ──────────────────────────────────────────────
_token_cache = {"access_token": None, "expires_at": 0, "refresh_token": None}

IOL_AUTH_URL  = "https://api.invertironline.com/token"
IOL_QUOTE_URL = "https://api.invertironline.com/api/v2/bCBA/Titulos/{ticker}/Cotizacion"

TICKERS = [
    "RC1CO","BYCHO","BACGO","BACHO","CAC5O","GN49O",
    "IRCPO","IRCFO","RUCDO","MGCMO","MGCOO","MGCRO",
    "PNXCO","PN43O","PLC4O","PLC5O","RAC7O","TTCAO",
    "TTCDO","TLCPO","TLCTO","TLCMO","TSC3O","TSC4O",
    "VSCTO","VSCVO","VSCXO","YMCIO","YMCJO","YMCXO",
    "YM34O","YFCJO",
]


async def get_token(client: httpx.AsyncClient, username: str, password: str) -> str:
    """Get a valid IOL access token, refreshing if needed."""
    now = time.time()

    # Still valid
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    # Try refresh first
    if _token_cache["refresh_token"]:
        try:
            r = await client.post(IOL_AUTH_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": _token_cache["refresh_token"],
            }, timeout=10)
            if r.status_code == 200:
                d = r.json()
                _token_cache["access_token"] = d["access_token"]
                _token_cache["refresh_token"] = d.get("refresh_token")
                _token_cache["expires_at"]    = now + int(d.get("expires_in", 1800))
                return _token_cache["access_token"]
        except Exception:
            pass

    # Full login
    r = await client.post(IOL_AUTH_URL, data={
        "username":   username,
        "password":   password,
        "grant_type": "password",
    }, timeout=10)

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="IOL authentication failed")

    d = r.json()
    _token_cache["access_token"] = d["access_token"]
    _token_cache["refresh_token"] = d.get("refresh_token")
    _token_cache["expires_at"]    = now + int(d.get("expires_in", 1800))
    return _token_cache["access_token"]


async def fetch_price(client: httpx.AsyncClient, ticker: str, token: str):
    """Fetch latest dirty price for one ticker from IOL."""
    try:
        r = await client.get(
            IOL_QUOTE_URL.format(ticker=ticker),
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if r.status_code == 200:
            d = r.json()
            # IOL devuelve 'ultimo' como el último precio operado
            price = (d.get("ultimo") or d.get("puntas", [{}])[0].get("precioVenta"))
            if price:
                return ticker, float(price)
    except Exception:
        pass
    return ticker, None


@app.get("/api/precios")
async def get_precios():
    import os
    username = os.environ.get("IOL_USER")
    password = os.environ.get("IOL_PASS")

    if not username or not password:
        raise HTTPException(
            status_code=503,
            detail="IOL_USER e IOL_PASS no configurados en las variables de entorno"
        )

    async with httpx.AsyncClient() as client:
        token   = await get_token(client, username, password)
        results = await asyncio.gather(
            *[fetch_price(client, tk, token) for tk in TICKERS]
        )

    precios = {tk: p for tk, p in results if p is not None}
    missing = [tk for tk, p in results if p is None]

    return {
        "precios":   precios,
        "timestamp": datetime.now().isoformat(),
        "total":     len(precios),
        "missing":   missing,
    }


@app.get("/api/status")
async def status():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# Serve static HTML — must go AFTER API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
