from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from datetime import datetime

app = FastAPI()

@app.get("/api/status")
async def status():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# Serve static HTML — must go AFTER API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
