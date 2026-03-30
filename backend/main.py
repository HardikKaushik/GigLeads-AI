import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root explicitly
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# Verify critical env var is loaded
if not os.getenv("XAI_API_KEY"):
    print(f"WARNING: XAI_API_KEY not found. Checked {_env_path} (exists={_env_path.exists()})")

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="GigLeads AI", version="0.1.0")

# CORS — auto-detect Render or use CORS_ORIGINS env var
_cors_origins = os.getenv("CORS_ORIGINS", "")
if _cors_origins:
    _allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
elif os.getenv("RENDER"):
    # On Render, allow all origins (the frontend URL is dynamic)
    _allowed_origins = ["*"]
else:
    _allowed_origins = ["http://localhost:3000", "http://localhost:3001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)
