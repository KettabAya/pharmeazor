"""FastAPI application serving the Pharmeazor interface.

Run it with::

    uvicorn pharmeazor.api.main:app --reload

The static front end in ``web/`` is served at ``/``. Endpoints that depend on a
built corpus answer 503 with an instruction rather than inventing data: the
whole point of the project is that nothing is displayed without a source.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config import ROOT, settings

app = FastAPI(
    title="Pharmeazor",
    description="Base de connaissances médicamenteuse et assistant à preuves.",
    version="0.1.0",
)

WEB_DIR = ROOT / "web"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    retriever: str | None = Field(
        default=None,
        description="Override the configured retriever ('bm25' or 'dense').",
    )


class CitationOut(BaseModel):
    source_id: str
    authority: str
    collected_at: str
    url: str
    quote: str


class AskResponse(BaseModel):
    short: str
    explanation: str
    citations: list[CitationOut]
    confidence: float
    limits: str
    numbers_checked: str
    refused: bool = False


@app.get("/api/health")
def health() -> dict:
    """Liveness plus a view of what is actually wired up."""
    index_built = (settings.processed_dir / "passages.jsonl").exists()
    return {
        "status": "ok",
        "version": app.version,
        "retriever": settings.retriever,
        "model_configured": bool(settings.model_name),
        "corpus_indexed": index_built,
    }


@app.get("/api/sources")
def sources() -> list[dict]:
    """The declared source registry with its compliance record."""
    from ..collect.registry import SourceRegistry

    try:
        registry = SourceRegistry.load()
    except FileNotFoundError as exc:
        raise HTTPException(503, "Registre des sources introuvable.") from exc
    except ModuleNotFoundError as exc:
        raise HTTPException(
            503, "PyYAML requis : pip install -r requirements.txt"
        ) from exc

    return [
        {
            "source_id": spec.source_id,
            "name": spec.name,
            "authority": spec.authority.label_fr,
            "rank": int(spec.authority),
            "access": spec.access,
            "robots_checked_on": (
                spec.robots_checked_on.isoformat() if spec.robots_checked_on else None
            ),
        }
        for spec in registry.by_authority()
    ]


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Answer a pharmacist's question with citations.

    Not yet wired: the retrieval and generation pipeline lands in week 3. Until
    the corpus is collected and indexed, this endpoint refuses rather than
    returning a plausible-looking answer with no source behind it.
    """
    if not (settings.processed_dir / "passages.jsonl").exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Corpus non indexé. Lancez `python scripts/collect.py` puis "
                "`python scripts/build_index.py` avant d'interroger l'assistant."
            ),
        )
    raise HTTPException(
        status_code=501,
        detail="Pipeline de réponse non encore implémenté (semaine 3).",
    )


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")
