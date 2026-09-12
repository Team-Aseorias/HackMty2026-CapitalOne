from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dashboard, decisions, evaluations, purchase_attempts

app = FastAPI(title="ANCLA API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(purchase_attempts.router)
app.include_router(decisions.router)
app.include_router(dashboard.router)
app.include_router(evaluations.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
