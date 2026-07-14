from sqlalchemy import select

from app.db import SessionLocal
from app.models import CollectorSource, TrainingDataset, TrainingExample
from app.schemas.research import ResearchCreate
from app.services.research import create_research, transition


def seed() -> None:
    with SessionLocal() as db:
        if not db.scalar(select(CollectorSource).where(CollectorSource.key == "openai-news")):
            db.add(
                CollectorSource(
                    key="openai-news",
                    name="OpenAI News",
                    type="rss",
                    url="https://openai.com/news/rss.xml",
                )
            )
            db.commit()
        if not db.scalar(select(TrainingExample).limit(1)):
            example = TrainingExample(
                instruction="Summarize the business value of an agent workflow.",
                context={"audience": "operations leader"},
                expected_response="Explain the outcome, controls, and measurable operating impact.",
                status="accepted",
                pii_status="clear",
                policy_status="approved",
                provenance={"source": "demo-seed"},
            )
            db.add(example)
            db.commit()
            dataset = TrainingDataset(
                name="Business agent demonstrations",
                version="demo-v1",
                description="Small governed dataset for local demonstration.",
                status="built",
                examples=[example],
            )
            db.add(dataset)
            db.commit()
        from app.models import ResearchItem

        if not db.scalar(select(ResearchItem).where(ResearchItem.title == "Research System MVP")):
            item = create_research(
                db,
                ResearchCreate(
                    title="Research System MVP",
                    summary="A local-first knowledge base for AI Agents for Business.",
                    content=(
                        "# Research System MVP\n\n"
                        "The system connects curated research, search, graph discovery, "
                        "AI enrichment, collection, and governed training data."
                    ),
                    tags=["AI Agents", "Business", "Knowledge Graph"],
                    authors=["Research Team"],
                ),
            )
            transition(db, item, "submit-review")
            transition(db, item, "approve")


if __name__ == "__main__":
    seed()
