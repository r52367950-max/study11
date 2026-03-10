import json
import os
import secrets
import time
from collections import defaultdict, deque
from difflib import SequenceMatcher
from typing import Deque
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import (
    build_report,
    get_profile,
    get_recent_timeline,
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
    MemoryTimelineResponse,
    PracticeSubmitRequest,
    SolveRequest,
    SolveResponse,
    StudyPlanRequest,
    StudyPlanResponse,
    TimelineItem,
)
from .tutor import generate_questions, generate_study_plan, solve_question

app = FastAPI(title="AI Tutor API", version="0.6.0")

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "120"))
RATE_LIMIT_WINDOW_S = int(os.getenv("RATE_LIMIT_WINDOW_S", "60"))
_request_buckets: dict[str, Deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _request_buckets[client_ip]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_S:
        bucket.popleft()

    if request.url.path != "/health" and len(bucket) >= RATE_LIMIT_COUNT:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "message": "Too many requests", "request_id": request_id},
        )

    bucket.append(now)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = request.headers.get("x-request-id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": str(exc.detail), "request_id": req_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = request.headers.get("x-request-id", "")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Unexpected server error", "request_id": req_id},
    )


@app.on_event("startup")
def on_startup():
    init_db()

# Ensure schema exists even when startup events are skipped in some test environments
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
            base_url=payload.model_settings.base_url,
            api_key=payload.model_settings.api_key,
            model=payload.model_settings.model,
            timeout_s=payload.model_settings.timeout_s,
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
            base_url=payload.model_settings.base_url,
            api_key=payload.model_settings.api_key,
            model=payload.model_settings.model,
            timeout_s=payload.model_settings.timeout_s,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model request failed: {exc}") from exc

    return GenerateResponse(
        questions=[str(x) for x in parsed.get("questions", [])][: payload.count],
        answers=[str(x) for x in parsed.get("answers", [])][: payload.count],
        explanations=[str(x) for x in parsed.get("explanations", [])][: payload.count],
    )


@app.post("/study/plan", response_model=StudyPlanResponse)
async def study_plan(payload: StudyPlanRequest):
    try:
        parsed = await generate_study_plan(
            subject=payload.subject,
            target=payload.target,
            weak_points=payload.weak_points,
            available_minutes_per_day=payload.available_minutes_per_day,
            days=payload.days,
            base_url=payload.model_settings.base_url,
            api_key=payload.model_settings.api_key,
            model=payload.model_settings.model,
            timeout_s=payload.model_settings.timeout_s,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model request failed: {exc}") from exc

    return StudyPlanResponse(**parsed)


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


@app.get("/memory/timeline", response_model=MemoryTimelineResponse)
def memory_timeline(
    user_id: str = Query(...),
    subject: str = Query("math"),
    limit: int = Query(20, ge=1, le=100),
):
    events = get_recent_timeline(user_id=user_id, subject=subject, limit=limit)
    return MemoryTimelineResponse(
        user_id=user_id,
        subject=subject,
        events=[TimelineItem(**item) for item in events],
    )
