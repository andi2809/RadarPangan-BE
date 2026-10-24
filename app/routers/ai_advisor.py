from fastapi import APIRouter
from app.schemas import EnvelopeResponse, AiBriefingRequest
from app.services.tpid_advisor_agent import run_tpid_advisor_briefing

router = APIRouter(prefix="/api/v1/ai", tags=["AI Policy Advisor"])

@router.post("/briefing", response_model=EnvelopeResponse[dict])
async def generate_ai_briefing(payload: AiBriefingRequest):
    """Menghasilkan nota dinas / rekomendasi strategis TPID dan Satgas Pangan
    yang diorkestrasi oleh Autonomous Agent Google Antigravity SDK."""
    briefing_text = await run_tpid_advisor_briefing(
        region_id=payload.region_id,
        commodity_id=payload.commodity_id,
        prompt=payload.pertanyaan_spesifik
    )
    return EnvelopeResponse(
        data={
            "region_id": payload.region_id,
            "commodity_id": payload.commodity_id,
            "agent_name": "Google Antigravity TPID Strategic Advisor",
            "executive_briefing_markdown": briefing_text
        }
    )
