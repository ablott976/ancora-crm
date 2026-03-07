import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db, close_db
from app.config import settings

from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.services import router as services_router
from app.routes.invoices import router as invoices_router
from app.routes.dashboard import router as dashboard_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    await init_db()
    # Optional: Initialize DB schema automatically
    # from app.database import get_db
    # async for conn in get_db():
    #     with open("app/sql/schema.sql", "r") as f:
    #         await conn.execute(f.read())
    #     break
    yield
    await close_db()

app = FastAPI(title="Ancora CRM API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(clients_router, prefix="/api/clients", tags=["clients"])
app.include_router(services_router, prefix="/api/services", tags=["services"])
app.include_router(invoices_router, prefix="/api/invoices", tags=["invoices"])

# SPA routing — backend serves frontend static files, catch-all returns index.html
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.api_route("/{path_name:path}", methods=["GET"])
    async def catch_all(request: Request, path_name: str):
        # Prevent API routes from being intercepted
        if path_name.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
            
        file_path = os.path.join(frontend_dist, path_name)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
            
        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
