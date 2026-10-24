from sqlalchemy import select

from app.db import SessionLocal
from app.models import CollectorSource
from app.schemas.research import ResearchCreate
from app.services.ontology import ensure_seed_ontology
from app.services.research import create_research, transition


def seed() -> None:
    with SessionLocal() as db:
        ensure_seed_ontology(db)
        if not db.scalar(select(CollectorSource).where(CollectorSource.key == "openai-news")):
            db.add(
                CollectorSource(
                    key="openai-news",
                    name="Tin tức OpenAI",
                    type="rss",
                    url="https://openai.com/news/rss.xml",
                )
            )
            db.commit()
        from app.models import ResearchItem

        if not db.scalar(
            select(ResearchItem).where(
                ResearchItem.title.in_({"Research System MVP", "Hệ thống nghiên cứu MVP"})
            )
        ):
            item = create_research(
                db,
                ResearchCreate(
                    title="Hệ thống nghiên cứu MVP",
                    summary="Kho tri thức cục bộ về tác nhân AI cho doanh nghiệp.",
                    content=(
                        "# Hệ thống nghiên cứu MVP\n\n"
                        "Hệ thống kết nối nghiên cứu đã tuyển chọn, tìm kiếm, khám phá đồ thị, "
                        "làm giàu bằng AI và thu thập nguồn."
                    ),
                    tags=["Tác nhân AI", "Doanh nghiệp", "Đồ thị tri thức"],
                    authors=["Nhóm nghiên cứu"],
                ),
            )
            transition(db, item, "submit-review")
            transition(db, item, "approve")


if __name__ == "__main__":
    seed()
