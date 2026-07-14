import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import TrainingDataset, TrainingEvent, TrainingExample
from app.schemas.training import DatasetBuild, DatasetCreate, EventCreate, ExampleUpdate

router = APIRouter(prefix="/training", tags=["training-data"])


def event_dict(event: TrainingEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "source": event.source,
        "payload": event.payload,
        "provenance": event.provenance,
        "created_at": event.created_at,
    }


def example_dict(example: TrainingExample) -> dict:
    return {
        "id": example.id,
        "event_id": example.event_id,
        "instruction": example.instruction,
        "context": example.context,
        "expected_response": example.expected_response,
        "status": example.status,
        "split": example.split,
        "pii_status": example.pii_status,
        "policy_status": example.policy_status,
        "provenance": example.provenance,
        "created_at": example.created_at,
        "updated_at": example.updated_at,
    }


def dataset_dict(dataset: TrainingDataset) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "version": dataset.version,
        "description": dataset.description,
        "status": dataset.status,
        "example_count": len(dataset.examples),
        "created_at": dataset.created_at,
    }


def get_example(db: Session, example_id: str) -> TrainingExample:
    example = db.scalar(select(TrainingExample).where(TrainingExample.id == example_id))
    if not example:
        raise HTTPException(404, "Training example not found")
    return example


def get_dataset(db: Session, dataset_id: str) -> TrainingDataset:
    dataset = db.scalar(
        select(TrainingDataset)
        .options(selectinload(TrainingDataset.examples))
        .where(TrainingDataset.id == dataset_id)
    )
    if not dataset:
        raise HTTPException(404, "Training dataset not found")
    return dataset


@router.post("/events", status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db)) -> dict:
    event = TrainingEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event_dict(event)


@router.get("/events")
def events(db: Session = Depends(get_db)) -> list[dict]:
    return [event_dict(event) for event in db.scalars(select(TrainingEvent))]


@router.post("/events/{event_id}/convert", status_code=201)
def convert(event_id: str, db: Session = Depends(get_db)) -> dict:
    event = db.scalar(select(TrainingEvent).where(TrainingEvent.id == event_id))
    if not event:
        raise HTTPException(404, "Training event not found")
    payload = event.payload
    if not payload.get("instruction") or not payload.get("expected_response"):
        raise HTTPException(422, "Event payload requires instruction and expected_response")
    example = TrainingExample(
        event_id=event.id,
        instruction=str(payload["instruction"]),
        context=payload.get("context", {}),
        expected_response=str(payload["expected_response"]),
        provenance={**event.provenance, "training_event_id": event.id, "source": event.source},
    )
    db.add(example)
    db.commit()
    db.refresh(example)
    return example_dict(example)


@router.get("/examples")
def examples(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    statement = select(TrainingExample).order_by(TrainingExample.created_at.desc())
    if status:
        statement = statement.where(TrainingExample.status == status)
    return [example_dict(example) for example in db.scalars(statement)]


@router.put("/examples/{example_id}")
def update_example(example_id: str, data: ExampleUpdate, db: Session = Depends(get_db)) -> dict:
    example = get_example(db, example_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(example, field, value)
    db.commit()
    db.refresh(example)
    return example_dict(example)


def set_example_status(db: Session, example_id: str, target: str) -> dict:
    example = get_example(db, example_id)
    if target == "accepted" and (
        example.pii_status not in {"clear", "anonymized"}
        or example.policy_status != "approved"
        or not example.provenance
    ):
        raise HTTPException(409, "PII, policy, and provenance checks are required")
    example.status = target
    db.commit()
    db.refresh(example)
    return example_dict(example)


@router.post("/examples/{example_id}/accept")
def accept(example_id: str, db: Session = Depends(get_db)) -> dict:
    return set_example_status(db, example_id, "accepted")


@router.post("/examples/{example_id}/reject")
def reject(example_id: str, db: Session = Depends(get_db)) -> dict:
    return set_example_status(db, example_id, "rejected")


@router.post("/examples/{example_id}/eval-only")
def eval_only(example_id: str, db: Session = Depends(get_db)) -> dict:
    example = get_example(db, example_id)
    example.split = "holdout"
    example.status = "eval-only"
    db.commit()
    return example_dict(example)


@router.get("/datasets")
def datasets(db: Session = Depends(get_db)) -> list[dict]:
    values = db.scalars(select(TrainingDataset).options(selectinload(TrainingDataset.examples)))
    return [dataset_dict(dataset) for dataset in values]


@router.post("/datasets", status_code=201)
def create_dataset(data: DatasetCreate, db: Session = Depends(get_db)) -> dict:
    dataset = TrainingDataset(**data.model_dump())
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset_dict(dataset)


@router.post("/datasets/{dataset_id}/build")
def build(dataset_id: str, data: DatasetBuild, db: Session = Depends(get_db)) -> dict:
    dataset = get_dataset(db, dataset_id)
    statement = select(TrainingExample).where(TrainingExample.status == "accepted")
    if data.example_ids is not None:
        statement = statement.where(TrainingExample.id.in_(data.example_ids))
    dataset.examples = list(db.scalars(statement))
    if not dataset.examples:
        raise HTTPException(409, "No accepted examples available")
    dataset.status = "built"
    db.commit()
    return dataset_dict(dataset)


@router.post("/datasets/{dataset_id}/export")
def export(dataset_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    dataset = get_dataset(db, dataset_id)
    if dataset.status != "built":
        raise HTTPException(409, "Build the dataset before export")
    rows = [
        json.dumps(
            {
                "instruction": item.instruction,
                "context": item.context,
                "expected_response": item.expected_response,
                "split": item.split,
                "provenance": item.provenance,
            },
            ensure_ascii=False,
        )
        for item in dataset.examples
    ]
    filename = f"{dataset.name}-{dataset.version}.jsonl".replace(" ", "-")
    return StreamingResponse(
        iter(["\n".join(rows) + "\n"]),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
