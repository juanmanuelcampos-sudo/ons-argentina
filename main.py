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

# Bonos para calcular CCL: AL30 (ARS) / AL30C (USD cable)
CCL_ARS_TICKER = "AL30"
CCL_USD_TICKER = "AL30C"


async def get_token(client: httpx.AsyncClient, username: str, password: str) -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]
    if _token_cache["refresh_token"]:
        try:
            r = await client.post(IOL_AUTH_URL, data={
                "grant_type":    "refresh_token",
                "refresh_token": _token_cache["refresh_token"],
            }, timeout=10)
            if r.status_code == 200:
                d = r.json()
                _token_cache["access_token"]  = d["access_token"]
                _token_cache["refresh_token"] = d.get("refresh_token")
                _token_cache["expires_at"]    = now + int(d.get("expires_in", 1800))
                return _token_cache["access_token"]
        except Exception:
            pass
    r = await client.post(IOL_AUTH_URL, data={
        "username":   username,
        "password":   password,
        "grant_type": "password",
    }, timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="IOL authentication failed")
    d = r.json()
    _token_cache["access_token"]  = d["access_token"]
    _token_cache["refresh_token"] = d.get("refresh_token")
    _token_cache["expires_at"]    = now + int(d.get("expires_in", 1800))
    return _token_cache["access_token"]


def extract_price(data: dict) -> float | None:
    """Extract last traded price from an IOL cotizacion response."""
    price = data.get("ultimo") or data.get("ultimoPrecio")
    if price:
        return float(price)
    # Fallback to best ask from puntas
    puntas = data.get("puntas") or []
    if puntas and puntas[0].get("precioVenta"):
        return float(puntas[0]["precioVenta"])
    return None


async def fetch_one(client: httpx.AsyncClient, ticker: str, token: str) -> tuple:
    try:
        r = await client.get(
            IOL_QUOTE_URL.format(ticker=ticker),
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if r.status_code == 200:
            return ticker, extract_price(r.json())
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
            detail="IOL_USER e IOL_PASS no configurados en las variables de entorno",
        )

    async with httpx.AsyncClient() as client:
        token = await get_token(client, username, password)

        # Fetch ONs + los dos tramos del CCL en paralelo
        all_tickers = TICKERS + [CCL_ARS_TICKER, CCL_USD_TICKER]
        results = await asyncio.gather(
            *[fetch_one(client, tk, token) for tk in all_tickers]
        )

    raw = {tk: p for tk, p in results if p is not None}

    # Calcular CCL = AL30 (ARS) / AL30C (USD cable)
    ccl = None
    al30_ars = raw.pop(CCL_ARS_TICKER, None)
    al30_usd = raw.pop(CCL_USD_TICKER, None)
    if al30_ars and al30_usd and al30_usd > 0:
        ccl = round(al30_ars / al30_usd, 4)

    # Convertir precios de ONs de ARS a USD
    precios_usd = {}
    missing = []
    for tk in TICKERS:
        p_ars = raw.get(tk)
        if p_ars is None:
            missing.append(tk)
        elif ccl and ccl > 0:
            precios_usd[tk] = round(p_ars / ccl, 4)
        else:
            # Sin CCL no podemos convertir — devolvemos el precio ARS con advertencia
            precios_usd[tk] = round(p_ars, 4)

    return {
        "precios":   precios_usd,
        "ccl":       ccl,
        "al30_ars":  al30_ars,
        "al30c_usd": al30_usd,
        "timestamp": datetime.now().isoformat(),
        "total":     len(precios_usd),
        "missing":   missing,
    }


@app.get("/api/status")
async def status():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
