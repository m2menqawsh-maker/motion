from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import projects, gates, render, brand, blueprint

app = FastAPI(title="Clean Video Workspace API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # GUI سيشتغل على 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(gates.router, prefix="/gates", tags=["gates"])
app.include_router(render.router, prefix="/render", tags=["render"])
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(blueprint.router, prefix="/blueprint", tags=["blueprint"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
