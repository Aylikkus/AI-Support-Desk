from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import tickets
from app.services.llm import check_llm

app = FastAPI(title="AI Support Desk")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)


@app.get("/api/llm/check")
def llm_check():
    result = check_llm()
    return JSONResponse(result, status_code=200 if result["ok"] else 502)


@app.get("/api/health")
def health():
    return {"status": "ok"}
