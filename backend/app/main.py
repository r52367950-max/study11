import json
import secrets
from difflib import SequenceMatcher

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import (
    build_report,
    get_profile,
    init_db,
    insert_dictation_record,
    upsert_practice,
)
from .schemas import (
    DictationStartRequest,
    DictationStartResponse,
    DictationSubmitRequest,
    DictationSubmitResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    MemoryProfile,
    MemoryReport,
    PracticeSubmitRequest,
    SolveRequest,
    SolveResponse,
)
from .tutor import generate_questions, solve_question

app = FastAPI(title="AI Tutor API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/subjects")
def subjects():
    return {"subjects": ["math", "english", "chinese"]}


@app.post("/math/solve", response_model=SolveResponse)
async def math_solve(payload: SolveRequest):
    try:
        parsed, used_search = await solve_question(
            question=payload.question,
            mode=payload.mode,
            base_url=payload.model_config.base_url,
            api_key=payload.model_config.api_key,
            model=payload.model_config.model,
            timeout_s=payload.model_config.timeout_s,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model request failed: {exc}") from exc

    return SolveResponse(
        analysis=str(parsed.get("analysis", "")),
        solution=str(parsed.get("solution", "")),
        pitfalls=[str(x) for x in parsed.get("pitfalls", [])][:5],
        practice_questions=[str(x) for x in parsed.get("practice_questions", [])][:2],
        used_search=used_search,
    )


@app.post("/math/generate", response_model=GenerateResponse)
async def math_generate(payload: GenerateRequest):
    try:
        parsed = await generate_questions(
            subject=payload.subject,
            difficulty=payload.difficulty,
            count=payload.count,
            constraints=payload.constraints,
            base_url=payload.model_config.base_url,
            api_key=payload.model_config.api_key,
            model=payload.model_config.model,
            timeout_s=payload.model_config.timeout_s,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model request failed: {exc}") from exc

    return GenerateResponse(
        questions=[str(x) for x in parsed.get("questions", [])][: payload.count],
        answers=[str(x) for x in parsed.get("answers", [])][: payload.count],
        explanations=[str(x) for x in parsed.get("explanations", [])][: payload.count],
    )


@app.post("/dictation/start", response_model=DictationStartResponse)
def dictation_start(payload: DictationStartRequest):
    session_id = secrets.token_urlsafe(8)
    return DictationStartResponse(session_id=session_id, content=payload.content, tts_text=payload.content)


@app.post("/dictation/submit", response_model=DictationSubmitResponse)
def dictation_submit(payload: DictationSubmitRequest):
    ref_tokens = payload.reference_text.strip().split()
    ans_tokens = payload.answer_text.strip().split()

    if payload.subject == "chinese":
        ref_tokens = list(payload.reference_text.strip())
        ans_tokens = list(payload.answer_text.strip())

    wrong_tokens = [token for token in ref_tokens if token not in ans_tokens][:10]
    similarity = SequenceMatcher(None, payload.reference_text, payload.answer_text).ratio()
    accuracy = round(similarity, 3)

    feedback = "整体不错，继续保持。"
    if accuracy < 0.7:
        feedback = "基础不稳，建议先做短句反复听写。"
    elif wrong_tokens:
        feedback = f"重点复习这些易错项：{', '.join(wrong_tokens[:3])}"

    insert_dictation_record(
        session_id=payload.session_id,
        user_id=payload.user_id,
        subject=payload.subject,
        reference_text=payload.reference_text,
        answer_text=payload.answer_text,
        accuracy=accuracy,
        wrong_tokens=wrong_tokens,
        duration_s=payload.duration_s,
    )

    upsert_practice(
        user_id=payload.user_id,
        subject=payload.subject,
        total=max(1, len(ref_tokens)),
        correct=max(0, len(ref_tokens) - len(wrong_tokens)),
        avg_duration_s=payload.duration_s,
        pitfall_hint=wrong_tokens[0] if wrong_tokens else None,
    )

    return DictationSubmitResponse(
        session_id=payload.session_id,
        accuracy=accuracy,
        wrong_tokens=wrong_tokens,
        feedback=feedback,
    )


@app.post("/practice/submit")
def submit_practice(payload: PracticeSubmitRequest):
    pitfall_hint = payload.notes.split("，")[0] if payload.notes else None
    upsert_practice(
        user_id=payload.user_id,
        subject=payload.subject,
        total=payload.total,
        correct=payload.correct,
        avg_duration_s=payload.avg_duration_s,
        pitfall_hint=pitfall_hint,
    )
    return {"status": "ok"}


@app.get("/memory/profile", response_model=MemoryProfile)
def memory_profile(user_id: str = Query(...), subject: str = Query("math")):
    row = get_profile(user_id=user_id, subject=subject)
    if not row:
        raise HTTPException(status_code=404, detail="profile not found")

    total_questions = max(1, row["total_questions"])
    accuracy = row["correct_total"] / total_questions

    return MemoryProfile(
        user_id=row["user_id"],
        subject=row["subject"],
        attempts=row["attempts"],
        accuracy=round(accuracy, 3),
        avg_duration_s=row["avg_duration_s"],
        top_pitfalls=json.loads(row["top_pitfalls"]),
        updated_at=row["updated_at"],
    )


@app.get("/memory/report", response_model=MemoryReport)
def memory_report(user_id: str = Query(...), subject: str = Query("math")):
    report = build_report(user_id=user_id, subject=subject)
    if not report:
        raise HTTPException(status_code=404, detail="profile not found")
    return MemoryReport(**report)
