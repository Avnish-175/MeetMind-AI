from typing import Any

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """Named entity recognized in the transcript text."""

    text: str
    label: str  # e.g., PERSON, ORG, DATE, GPE, MONEY, TIME
    transcript_segment_ids: list[int] = Field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None


class ExtractedKeyword(BaseModel):
    """Keyword or salient phrase extracted with statistical score."""

    text: str
    score: float
    transcript_segment_ids: list[int] = Field(default_factory=list)


class SentenceInsight(BaseModel):
    """Sentence-level segmented unit with timing association."""

    text: str
    transcript_segment_id: int | None = None
    start_time: float | None = None
    end_time: float | None = None


class LinguisticMetadata(BaseModel):
    """Corpus-level metrics derived from linguistic analysis."""

    total_tokens: int
    total_sentences: int
    unique_lemmas: int
    entity_counts_by_type: dict[str, int] = Field(default_factory=dict)
    topic_keywords: list[str] = Field(default_factory=list)


class TraditionalNLPResult(BaseModel):
    """Comprehensive structured outcome of traditional NLP processing on a transcript."""

    keywords: list[ExtractedKeyword] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)
    sentences: list[SentenceInsight] = Field(default_factory=list)
    metadata: LinguisticMetadata
