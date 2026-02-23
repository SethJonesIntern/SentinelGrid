from fastapi import FastAPI
from app.db.database import engine
from app.db.base import Base
from app.routes.health import router as health_router
from app.routes.log import router as log_router
from app.routes.sessions import router as sessions_router

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(log_router)
app.include_router(sessions_router)