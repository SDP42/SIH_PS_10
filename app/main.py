import os
from dotenv import load_dotenv

load_dotenv()  # picks up ICD_API_CLIENT_ID / ICD_API_CLIENT_SECRET etc. from .env if present

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app import conceptmap, api, ai_router, governance, governance_router, fhir_extra, auth, audit, problem_list, consent, who_sync, who_router, analytics_router, clinical_text_router, apikeys, apikey_router, v1_router, population_analytics_router, terminology_simulator, terminology_simulator_router

governance.ensure_schema()
audit.ensure_schema()
who_sync.ensure_schema()
apikeys.ensure_schema()
terminology_simulator.ensure_schema()

app = FastAPI(
    title="Ayush ICD-11 Terminology Microservice",
    version="0.1.0",
    description="FHIR-compliant terminology service for mapping NAMASTE Ayurveda codes to ICD-11"
)

# CORS — allow localhost dev + any production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers FIRST so they take priority over static file catch-all
# fhir_extra registers /ConceptMap/$translate — must be mounted BEFORE
# conceptmap.router's /ConceptMap/{source_code}, otherwise that path-param
# route would swallow "$translate" as a literal source_code (first-match-wins
# routing).
app.include_router(fhir_extra.router)
app.include_router(conceptmap.router, tags=["ConceptMap"])
app.include_router(api.router, prefix="/api", tags=["API"])
app.include_router(ai_router.router)
app.include_router(governance_router.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(problem_list.router)
app.include_router(consent.router)
app.include_router(who_router.router)
app.include_router(analytics_router.router)
app.include_router(clinical_text_router.router)
app.include_router(apikey_router.router)
app.include_router(v1_router.router)
app.include_router(population_analytics_router.router)
app.include_router(terminology_simulator_router.router)

# Serve React frontend static files if the dist directory exists
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    def serve_root():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Catch-all: return index.html for React Router client-side routing."""
        # Don't intercept API / ConceptMap routes
        if full_path.startswith("api/") or full_path.startswith("ConceptMap"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

else:
    # Fallback JSON root when no frontend build is present
    @app.get("/")
    def root():
        return {
            "message": "AYUSH ICD-11 Terminology Microservice",
            "version": "0.1.0",
            "endpoints": {
                "concept_maps": "/ConceptMap",
                "specific_mapping": "/ConceptMap/{code}",
                "docs": "/docs",
                "stats": "/api/stats",
                "search": "/api/search",
                "concepts": "/api/concepts",
                "mappings": "/api/mappings",
            }
        }
