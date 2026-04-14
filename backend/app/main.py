from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, SessionLocal, Base
from app.models import *  # noqa: ensure all models are registered
from app.routes_auth import router as auth_router
from app.routes_broadcasters import router as broadcasters_router
from app.routes_policies import router as policies_router
from app.routes_tech_items import router as tech_items_router
from app.routes_mappings import router as mappings_router
from app.routes_test import router as test_router
from app.seed import seed

app = FastAPI(title="AirRule API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(broadcasters_router)
app.include_router(policies_router)
app.include_router(tech_items_router)
app.include_router(mappings_router)
app.include_router(test_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
