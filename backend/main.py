"""
Dashboard SO C383 — FastAPI Backend (FINAL FIX)
"""
import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ✅ TAMBAHIN IMPORT REALTIME & SERVICE
from routers import kurumi, hana, yui, rei, config, auth, proxy, broadcast, room, realtime
from services.supabase_listener import start_supabase_listener
from middleware.auth import AuthMiddleware
from middleware.rate_limit import setup_rate_limit

app = FastAPI(title="Dashboard SO C383 API", version="1.0.0", docs_url="/docs")

# =========================================================
# STARTUP EVENT (Nyalain Listener)
# =========================================================
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_supabase_listener())

# =========================================================
# MIDDLEWARE — URUTAN PALING PENTING!
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)
setup_rate_limit(app)

# =========================================================
# ROUTERS
# =========================================================
app.include_router(auth.router)
app.include_router(kurumi.router)
app.include_router(hana.router)
app.include_router(yui.router)
app.include_router(rei.router)
app.include_router(config.router)
app.include_router(proxy.router, prefix="/api/proxy")
app.include_router(broadcast.router)
app.include_router(room.router)
app.include_router(realtime.router) # ✅ DAFTARIN ROUTER REALTIME

# =========================================================
# HEALTH
# =========================================================
@app.get("/")
async def root():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[ERROR] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": "Terjadi kesalahan internal."},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )