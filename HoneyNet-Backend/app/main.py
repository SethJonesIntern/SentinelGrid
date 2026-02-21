from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.log import router as log_router
from app.routes.sessions import router as sessions_router

app = FastAPI()

app.include_router(health_router)
app.include_router(log_router)
app.include_router(sessions_router)