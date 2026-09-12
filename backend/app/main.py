from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.mongo import ping, ensure_indexes, close_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    ok = await ping()
    if not ok:
        raise RuntimeError("No se pudo conectar a MongoDB")
    await ensure_indexes()
    yield
    await close_client()


app = FastAPI(title="ANCLA API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": await ping()}