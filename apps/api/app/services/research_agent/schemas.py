"""Schema đầu ra của từng agent.

Mọi trường đều bắt buộc và không có mặc định để dùng được với structured output chế độ strict
(OpenAI/Mistral/OpenRouter) lẫn CLI bridge; giới hạn số lượng áp ở phía máy chủ sau khi parse.
"""

from typing import Literal

from pydantic import BaseModel

Perspective = Literal["market", "use_case", "competitors", "technical", "risk_compliance"]
PERSPECTIVES: tuple[Perspective, ...] = (
    "market",
    "use_case",
    "competitors",
    "technical",
    "risk_compliance",
)
PERSPECTIVE_LABELS: dict[str, str] = {
    "summary": "Tóm tắt",
    "market": "Thị trường",
    "use_case": "Use case",
    "competitors": "Đối thủ",
    "technical": "Kỹ thuật",
    "risk_compliance": "Rủi ro & tuân thủ",
}


class PlannedQuery(BaseModel):
    perspective: Perspective
    query: str


class ResearchPlan(BaseModel):
    restated_question: str
    queries: list[PlannedQuery]


class ExtractedClaim(BaseModel):
    source_id: str
    perspective: Perspective
    claim: str
    quote: str


class ClaimExtraction(BaseModel):
    claims: list[ExtractedClaim]


class EntailmentJudgement(BaseModel):
    claim_id: str
    verdict: Literal["supported", "partial", "not_supported"]


class EntailmentBatch(BaseModel):
    judgements: list[EntailmentJudgement]


class ReportSentence(BaseModel):
    text: str
    claim_ids: list[str]


class ReportSection(BaseModel):
    perspective: Literal[
        "summary", "market", "use_case", "competitors", "technical", "risk_compliance"
    ]
    sentences: list[ReportSentence]


class ReportDraft(BaseModel):
    title: str
    sections: list[ReportSection]
