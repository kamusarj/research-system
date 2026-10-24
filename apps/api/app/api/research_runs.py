import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.identity import current_principal, has_role
from app.db import SessionLocal, get_db
from app.models import (
    KnowledgeGap,
    ResearchRun,
    ResearchRunClaim,
    ResearchRunEvent,
    ResearchRunSource,
)
from app.schemas.research_runs import (
    ResearchRunClaimRead,
    ResearchRunCreate,
    ResearchRunDetail,
    ResearchRunEventRead,
    ResearchRunList,
    ResearchRunRead,
    ResearchRunSourceRead,
)
from app.services.object_storage import DocumentError
from app.services.research_agent.runner import create_run, request_cancel, retry_run

router = APIRouter(prefix="/research-runs", tags=["research-agent"])

TERMINAL = {"completed", "failed", "cancelled"}
SSE_POLL_SECONDS = 1.0
SSE_MAX_SECONDS = 150.0
SSE_KEEPALIVE_SECONDS = 15.0


def get_run(db: Session, run_id: str) -> ResearchRun:
    run = db.get(ResearchRun, run_id)
    if run is None:
        raise DocumentError("RESEARCH_RUN_NOT_FOUND", "Không tìm thấy lượt nghiên cứu", 404)
    return run


def _ensure_owner_or_creator(run: ResearchRun) -> None:
    principal = current_principal()
    if principal is None or principal.id == run.created_by or has_role(principal.role, "owner"):
        return
    raise DocumentError("ACCESS_DENIED", "Chỉ người tạo hoặc chủ sở hữu được thao tác", 403)


def serialize_run(run: ResearchRun) -> ResearchRunRead:
    return ResearchRunRead(
        id=run.id,
        question=run.question,
        status=run.status,
        stage=run.stage,
        variant=run.variant,
        provider_name=run.provider_name,
        model_name=run.model_name,
        knowledge_gap_id=run.knowledge_gap_id,
        report_research_id=run.report_research_id,
        error_code=run.error_code,
        error_message=run.error_message,
        metrics=run.metrics_json or {},
        created_by=run.created_by,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _events(db: Session, run_id: str, after: int, limit: int = 200) -> list[ResearchRunEventRead]:
    rows = db.scalars(
        select(ResearchRunEvent)
        .where(ResearchRunEvent.run_id == run_id, ResearchRunEvent.id > after)
        .order_by(ResearchRunEvent.id)
        .limit(limit)
    )
    return [
        ResearchRunEventRead(
            id=row.id,
            kind=row.kind,
            stage=row.stage,
            message=row.message,
            data=row.data or {},
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("", response_model=ResearchRunRead, status_code=202)
def start_run(data: ResearchRunCreate, db: Session = Depends(get_db)) -> ResearchRunRead:
    if data.knowledge_gap_id and db.get(KnowledgeGap, data.knowledge_gap_id) is None:
        raise DocumentError("KNOWLEDGE_GAP_NOT_FOUND", "Không tìm thấy khoảng trống tri thức", 404)
    run = create_run(
        db, data.question, variant=data.variant, knowledge_gap_id=data.knowledge_gap_id
    )
    return serialize_run(run)


@router.get("", response_model=ResearchRunList)
def list_runs(
    db: Session = Depends(get_db),
    mine: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ResearchRunList:
    statement = select(ResearchRun)
    if mine:
        principal = current_principal()
        statement = statement.where(
            ResearchRun.created_by == (principal.id if principal else "local-user")
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(ResearchRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ResearchRunList(items=[serialize_run(run) for run in rows], total=total)


@router.get("/{run_id}", response_model=ResearchRunDetail)
def run_detail(run_id: str, db: Session = Depends(get_db)) -> ResearchRunDetail:
    run = get_run(db, run_id)
    sources = db.scalars(
        select(ResearchRunSource)
        .where(ResearchRunSource.run_id == run.id)
        .order_by(
            ResearchRunSource.citation_index.is_(None),
            ResearchRunSource.citation_index,
            ResearchRunSource.rank,
        )
    )
    claims = db.scalars(
        select(ResearchRunClaim)
        .where(ResearchRunClaim.run_id == run.id)
        .order_by(ResearchRunClaim.used_in_report.desc(), ResearchRunClaim.status)
    )
    return ResearchRunDetail(
        **serialize_run(run).model_dump(),
        report_markdown=run.report_markdown,
        sources=[
            ResearchRunSourceRead(
                id=s.id,
                provider=s.provider,
                perspective=s.perspective,
                url=s.url,
                domain=s.domain,
                title=s.title,
                status=s.status,
                suspicious=s.suspicious,
                citation_index=s.citation_index,
                error_code=s.error_code,
            )
            for s in sources
        ],
        claims=[
            ResearchRunClaimRead(
                id=c.id,
                source_id=c.source_id,
                perspective=c.perspective,
                text=c.text,
                quote=c.quote,
                matched_quote=c.matched_quote,
                match_method=c.match_method,
                entailment=c.entailment,
                status=c.status,
                reason=c.reason,
                used_in_report=c.used_in_report,
            )
            for c in claims
        ],
        events=_events(db, run.id, 0),
    )


@router.get("/{run_id}/events", response_model=list[ResearchRunEventRead])
def run_events(
    run_id: str, after: int = Query(0, ge=0), db: Session = Depends(get_db)
) -> list[ResearchRunEventRead]:
    get_run(db, run_id)
    return _events(db, run_id, after)


@router.get("/{run_id}/events/stream")
async def run_event_stream(
    run_id: str,
    request: Request,
    after: int = Query(0, ge=0),
    last_event_id: str | None = Header(default=None),
) -> StreamingResponse:
    """Server-Sent Events. Mỗi vòng dùng phiên DB ngắn để luồng mở không giữ kết nối pool; tự
    đóng sau 150 giây (proxy Next.js cắt ở 180 giây), trình duyệt nối lại bằng Last-Event-ID."""
    with SessionLocal() as db:
        get_run(db, run_id)
    cursor = max(after, int(last_event_id) if last_event_id and last_event_id.isdigit() else 0)

    async def stream() -> AsyncIterator[str]:
        nonlocal cursor
        started = time.monotonic()
        last_sent = started
        yield "retry: 2000\n\n"
        while time.monotonic() - started < SSE_MAX_SECONDS:
            if await request.is_disconnected():
                return
            with SessionLocal() as db:
                events = _events(db, run_id, cursor)
                run = db.get(ResearchRun, run_id)
                status = run.status if run else "failed"
            for event in events:
                cursor = event.id
                payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                yield f"id: {event.id}\nevent: {event.kind}\ndata: {payload}\n\n"
                last_sent = time.monotonic()
            if status in TERMINAL and not events:
                yield f"event: end\ndata: {json.dumps({'status': status})}\n\n"
                return
            if time.monotonic() - last_sent > SSE_KEEPALIVE_SECONDS:
                yield ": keepalive\n\n"
                last_sent = time.monotonic()
            await asyncio.sleep(SSE_POLL_SECONDS)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post("/{run_id}/cancel", response_model=ResearchRunRead)
def cancel_run(run_id: str, db: Session = Depends(get_db)) -> ResearchRunRead:
    run = get_run(db, run_id)
    _ensure_owner_or_creator(run)
    return serialize_run(request_cancel(db, run))


@router.post("/{run_id}/retry", response_model=ResearchRunRead, status_code=202)
def retry(run_id: str, db: Session = Depends(get_db)) -> ResearchRunRead:
    run = get_run(db, run_id)
    _ensure_owner_or_creator(run)
    return serialize_run(retry_run(db, run))


@router.get("/{run_id}/export.md", response_class=PlainTextResponse)
def export_markdown(run_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    run = get_run(db, run_id)
    if not run.report_markdown:
        raise DocumentError("RESEARCH_REPORT_NOT_READY", "Báo cáo chưa sẵn sàng", 409)
    return PlainTextResponse(
        run.report_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="research-{run.id[:8]}.md"',
            "X-Content-Type-Options": "nosniff",
        },
    )
