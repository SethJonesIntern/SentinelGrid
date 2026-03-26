from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.log import router as log_router
from app.routes.logs import router as sessions_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(log_router)
app.include_router(sessions_router)