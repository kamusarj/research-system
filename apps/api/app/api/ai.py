from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AIOutput
from app.schemas.research import ResearchUpdate
from app.services.ai import provider_status, run_enrichment
from app.services.research import get_research_or_404, serialize_research, update_research

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/providers")
def providers() -> list[dict]:
    return provider_status()


def output_dict(output: AIOutput) -> dict:
    return {
        "id": output.id,
        "research_id": output.research_id,
        "task": output.task,
        "model_name": output.model_name,
        "model_version": output.model_version,
        "prompt_version": output.prompt_version,
        "input_hash": output.input_hash,
        "output": output.output_json,
        "confidence": output.confidence,
        "created_at": output.created_at,
    }


def run_from_payload(task: str, payload: dict[str, str], db: Session) -> dict:
    research_id = payload.get("research_id")
    if not research_id:
        raise HTTPException(422, "research_id is required")
    return output_dict(run_enrichment(db, get_research_or_404(db, research_id), task))


@router.post("/summarize")
def summarize(payload: dict[str, str], db: Session = Depends(get_db)) -> dict:
    return run_from_payload("summarize", payload, db)


@router.post("/extract-concepts")
def concepts(payload: dict[str, str], db: Session = Depends(get_db)) -> dict:
    return run_from_payload("extract-concepts", payload, db)


@router.post("/suggest-relations")
def relations(payload: dict[str, str], db: Session = Depends(get_db)) -> dict:
    return run_from_payload("suggest-relations", payload, db)


@router.post("/enrich/{research_id}")
def enrich(research_id: str, db: Session = Depends(get_db)) -> dict:
    return output_dict(run_enrichment(db, get_research_or_404(db, research_id)))


@router.post("/outputs/{output_id}/accept")
def accept_output(output_id: str, db: Session = Depends(get_db)) -> dict:
    output = db.scalar(select(AIOutput).where(AIOutput.id == output_id))
    if not output or not output.research_id:
        raise HTTPException(404, "AI output not found")
    item = get_research_or_404(db, output.research_id)
    values = output.output_json
    update = ResearchUpdate(
        summary=values.get("summary", item.summary),
        tags=values.get("tags", [tag.display_name for tag in item.tags]),
    )
    updated = update_research(db, item, update)
    return serialize_research(updated).model_dump(mode="json")
