from fastapi import FastAPI
from app.db.database import engine
from app.db.base import Base
from app.routes.health import router as health_router
from app.routes.log import router as log_router
from app.routes.logs import router as sessions_router
from app.routes.ml import router as ml_router
from app.routes.auth import router as auth_router
from app.routes.geo import router as geo_router
from app.services.ml_scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    # Kick off the ML plan refresher (no-op unless ML_SCHEDULER_ENABLED is set).
    start_scheduler()

app.include_router(health_router)
app.include_router(log_router)
app.include_router(sessions_router)
app.include_router(ml_router)
app.include_router(auth_router)
app.include_router(geo_router)