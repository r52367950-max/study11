import json

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import build_report, get_profile, init_db, upsert_practice
from .schemas import (
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

app = FastAPI(title="AI Tutor API", version="0.3.0")

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
