"""PaperCard quality report schemas."""

from pydantic import BaseModel, Field


class FieldQuality(BaseModel):
    """Quality signals for one PaperCard field."""

    field: str
    values_count: int = 0
    cited_values_count: int = 0
    missing: bool = False
    citation_coverage: float = 0.0
    suspicious_values: list[str] = Field(default_factory=list)
    expected_values: list[str] = Field(default_factory=list)
    matched_expected_values: list[str] = Field(default_factory=list)
    precision: float | None = None
    recall: float | None = None


class PaperCardQualityReport(BaseModel):
    """A compact, explainable quality report for PaperCard review."""

    paper_id: str
    completeness: float
    citation_coverage: float
    suspicious_values_count: int
    fields: list[FieldQuality]
    warnings: list[str] = Field(default_factory=list)
    golden_available: bool = False
    macro_precision: float | None = None
    macro_recall: float | None = None
