from pydantic import BaseModel, Field


class CustomTypeSpec(BaseModel):
    name: str
    pattern: str
    context_words: list[str] = Field(default_factory=list)
    score_threshold: float
    finding_type: str = "custom"
