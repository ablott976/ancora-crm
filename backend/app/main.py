import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db, close_db
from app.redis_client import init_redis, close_redis
from app.config import settings

from app.routes.auth import router as auth_router
from app.routes.clients import router as clients_router
from app.routes.services import router as services_router
from app.routes.invoices import router as invoices_router
from app.routes.dashboard import router as dashboard_router
from app.routes.chatbot_webhook import router as chatbot_webhook_router
from app.routes.chatbot_dashboard import router as chatbot_dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    await init_db()
    await init_redis()

    # Register all plugins
    from app.plugins import register_all_plugins, PluginRegistry
    register_all_plugins()

    # Mount plugin routers
    for plugin in PluginRegistry.all_plugins():
        plugin_router = plugin.get_router()
        if plugin_router:
            app.include_router(plugin_router, prefix="/api/chatbot", tags=[f"plugin_{plugin.id}"])

    yield
    await close_db()
    await close_redis()

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
app.include_router(chatbot_webhook_router, prefix="/api/chatbot", tags=["chatbot_webhook"])
app.include_router(chatbot_dashboard_router, prefix="/api/chatbot", tags=["chatbot_dashboard"])

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# SPA routing
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")

if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.api_route("/{path_name:path}", methods=["GET"])
    async def catch_all(request: Request, path_name: str):
        if path_name.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        file_path = os.path.join(frontend_dist, path_name)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

        return JSONResponse(status_code=404, content={"detail": "Frontend not built"})
