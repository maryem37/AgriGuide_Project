"""Point d'entrée de l'API FastAPI de l'agent de régulation agricole.

Lancement local : uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="Agent de Régulation Agricole")

# Dev only : le frontend (Vite) tourne sur un port différent de ce service.
# À restreindre à l'origine réelle du frontend une fois déployé.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    """Vérifie que l'API est disponible."""
    return {"status": "ok"}
