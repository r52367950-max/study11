from pydantic import BaseModel, Field, field_validator

ALLOWED_SUBJECTS = {"math", "english", "chinese"}


class ModelConfig(BaseModel):
    provider: str = Field(default="openai_compatible")
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: str
    model: str = Field(default="gpt-4o-mini")
    timeout_s: int = Field(default=60, ge=5, le=180)


class SolveRequest(BaseModel):
    user_id: str
    question: str = Field(min_length=3)
    subject: str = Field(default="math")
    mode: str = Field(default="full", description="hint | full")
    model_config: ModelConfig

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_SUBJECTS:
            raise ValueError(f"subject must be one of {sorted(ALLOWED_SUBJECTS)}")
        return normalized

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"hint", "full"}:
            raise ValueError("mode must be 'hint' or 'full'")
        return normalized


class SolveResponse(BaseModel):
    analysis: str
    solution: str
    pitfalls: list[str]
    practice_questions: list[str]
    used_search: bool


class GenerateRequest(BaseModel):
    user_id: str
    subject: str = Field(default="math")
    difficulty: str = Field(default="medium")
    count: int = Field(default=3, ge=1, le=10)
    constraints: str | None = None
    model_config: ModelConfig

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_SUBJECTS:
            raise ValueError(f"subject must be one of {sorted(ALLOWED_SUBJECTS)}")
        return normalized


class GenerateResponse(BaseModel):
    questions: list[str]
    answers: list[str]
    explanations: list[str]


class PracticeSubmitRequest(BaseModel):
    user_id: str
    subject: str = Field(default="math")
    total: int = Field(ge=1)
    correct: int = Field(ge=0)
    avg_duration_s: int = Field(ge=1)
    notes: str | None = None

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_SUBJECTS:
            raise ValueError(f"subject must be one of {sorted(ALLOWED_SUBJECTS)}")
        return normalized

    @field_validator("correct")
    @classmethod
    def validate_correct(cls, value: int, info):
        total = info.data.get("total")
        if total is not None and value > total:
            raise ValueError("correct cannot be greater than total")
        return value


class DictationStartRequest(BaseModel):
    user_id: str
    subject: str = Field(default="english")
    content: str = Field(min_length=1, description="待听写文本")

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"english", "chinese"}:
            raise ValueError("dictation subject must be 'english' or 'chinese'")
        return normalized


class DictationStartResponse(BaseModel):
    session_id: str
    content: str
    tts_text: str


class DictationSubmitRequest(BaseModel):
    session_id: str
    user_id: str
    subject: str = Field(default="english")
    reference_text: str = Field(min_length=1)
    answer_text: str = Field(min_length=1)
    duration_s: int = Field(default=30, ge=1)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"english", "chinese"}:
            raise ValueError("dictation subject must be 'english' or 'chinese'")
        return normalized


class DictationSubmitResponse(BaseModel):
    session_id: str
    accuracy: float
    wrong_tokens: list[str]
    feedback: str


class MemoryProfile(BaseModel):
    user_id: str
    subject: str
    attempts: int
    accuracy: float
    avg_duration_s: int
    top_pitfalls: list[str]
    updated_at: str


class MemoryReport(BaseModel):
    user_id: str
    subject: str
    level: str
    trend: str
    attempts: int
    accuracy: float
    top_pitfalls: list[str]
    suggestions: list[str]
    dictation_sessions: int
    dictation_accuracy: float


class HealthResponse(BaseModel):
    status: str
