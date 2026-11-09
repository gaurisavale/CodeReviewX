"""Request and response schemas (OpenAPI is generated from these)."""
from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Python source to analyse")
    language: str = "python"
    filename: Optional[str] = "example.py"
    project_id: Optional[int] = Field(None, description="Attach the run to a project so its history is tracked")
    save: bool = Field(True, description="Store the run in the history database")


class GithubRequest(BaseModel):
    url: str = Field(..., examples=["https://github.com/pallets/click"])
    project_id: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
