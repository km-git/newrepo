from pydantic import BaseModel, Field


class ControlHit(BaseModel):
    framework: str
    control_id: str
    title: str
    status: str
    matched_types: list[str] = Field(default_factory=list)
