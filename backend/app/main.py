import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api import operator, tickets
from app.services import llm as llm_service
from app.services.graph import init_graph_runtime
from app.services.knowledge_base import init_knowledge_base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        kb = init_knowledge_base()
        logger.info("Knowledge base loaded: %d entries", len(kb.entries))
    except OSError as exc:
        logger.warning("Knowledge base not loaded (%s); the graph will answer without it", exc)
    await run_in_threadpool(init_graph_runtime)
    yield


app = FastAPI(title="AI Support Desk", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080", "http://localhost:8010"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(operator.router)


@app.get("/api/llm/check")
async def llm_check():
    result = await run_in_threadpool(llm_service.check_llm)
    return JSONResponse(result, status_code=200 if result["ok"] else 502)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
