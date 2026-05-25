from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

from routers import analyze, briefs

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("TrendSpy API starting up...")
    yield
    print("TrendSpy API shutting down...")

app = FastAPI(
    title="TrendSpy API",
    description="Real-time market intelligence via SSE streaming",
    version="1.0.0",
    lifespan=lifespan
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, tags=["Analysis"])
app.include_router(briefs.router, prefix="/briefs", tags=["Briefs"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "service": "TrendSpy"}
