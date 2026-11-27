from collections import Counter
import logging
import re
import threading
from typing import Any

from app.schemas.nlp import (
    ExtractedEntity,
    ExtractedKeyword,
    LinguisticMetadata,
    SentenceInsight,
    TraditionalNLPResult,
)

logger = logging.getLogger(__name__)

_nlp_lock = threading.Lock()
_cached_spacy_nlp: Any = None
_cached_is_fallback: bool = False
_cached_warning: str | None = None
SPACY_MODEL_NAME = "en_core_web_sm"

FULL_MODEL_CAPABILITIES = [
    "sentencizer",
    "tokenization",
    "lemmatization",
    "pos_tagging",
    "ner",
    "noun_chunks",
]
FALLBACK_CAPABILITIES = [
    "sentencizer",
    "tokenization",
]


def _get_spacy_model() -> tuple[Any, bool, str | None]:
    """Lazily load and cache the English spaCy language model.

    Returns (nlp_pipeline, is_fallback, warning_message).
    """
    global _cached_spacy_nlp, _cached_is_fallback, _cached_warning
    with _nlp_lock:
        if _cached_spacy_nlp is not None:
            return _cached_spacy_nlp, _cached_is_fallback, _cached_warning

        try:
            import spacy
        except ImportError as exc:
            logger.error("spaCy is not installed in the environment: %s", exc)
            raise RuntimeError("spaCy is not installed in the backend environment.") from exc

        try:
            logger.info("Loading spaCy model '%s'...", SPACY_MODEL_NAME)
            _cached_spacy_nlp = spacy.load(SPACY_MODEL_NAME)
            _cached_is_fallback = False
            _cached_warning = None
            logger.info("spaCy model '%s' loaded successfully.", SPACY_MODEL_NAME)
        except Exception:
            warning_msg = (
                f"spaCy model '{SPACY_MODEL_NAME}' is not installed; using blank English "
                "fallback. Named entity recognition, POS tagging, noun chunks, and "
                "lemmatization are disabled."
            )
            logger.warning(warning_msg)
            try:
                nlp_fallback = spacy.blank("en")
                if "sentencizer" not in nlp_fallback.pipe_names:
                    nlp_fallback.add_pipe("sentencizer")
                _cached_spacy_nlp = nlp_fallback
                _cached_is_fallback = True
                _cached_warning = warning_msg
            except Exception as inner_exc:
                raise RuntimeError(
                    f"Failed to initialize any spaCy English pipeline: {inner_exc}"
                ) from inner_exc

        return _cached_spacy_nlp, _cached_is_fallback, _cached_warning


def _extract_tfidf_keywords(
    segment_texts: list[str],
    top_n: int = 15,
) -> list[tuple[str, float]]:
    """Extract top keywords across transcript segments using Scikit-learn TF-IDF."""
    non_empty_texts = [text.strip() for text in segment_texts if text.strip()]
    if not non_empty_texts:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.warning("scikit-learn is not available; falling back to frequency-based keywords.")
        words = re.findall(r"\b[a-zA-Z]{3,}\b", " ".join(non_empty_texts).lower())
        common = Counter(words).most_common(top_n)
        return [(word, float(count)) for word, count in common]

    try:
        # When there is only 1 segment, max_df=0.95 would evaluate to 0 documents and raise ValueError.
        max_df = 1.0 if len(non_empty_texts) == 1 else 0.95
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_df=max_df,
            min_df=1,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
        )
        matrix = vectorizer.fit_transform(non_empty_texts)
        feature_names = vectorizer.get_feature_names_out()
        scores = matrix.sum(axis=0).A1
        ranked_indices = scores.argsort()[::-1][:top_n]
        return [(str(feature_names[i]), round(float(scores[i]), 3)) for i in ranked_indices]
    except Exception as exc:
        logger.warning("TF-IDF keyword extraction failed: %s", exc)
        return []


def process_meeting_transcript_nlp(
    full_text: str,
    segments: list[dict[str, Any]],
) -> TraditionalNLPResult:
    """Run traditional NLP on transcript segments preserving timestamps and segment associations."""
    nlp, is_fallback, warning_msg = _get_spacy_model()
    pipeline_name = "spacy:blank_en_fallback" if is_fallback else f"spacy:{SPACY_MODEL_NAME}"
    capabilities = list(FALLBACK_CAPABILITIES if is_fallback else FULL_MODEL_CAPABILITIES)

    if not full_text or not full_text.strip():
        return TraditionalNLPResult(
            keywords=[],
            entities=[],
            key_phrases=[],
            sentences=[],
            metadata=LinguisticMetadata(
                total_tokens=0,
                total_sentences=0,
                unique_lemmas=0,
                entity_counts_by_type={},
                topic_keywords=[],
                nlp_pipeline=pipeline_name,
                capabilities=capabilities,
                warning=warning_msg,
            ),
        )

    sentences: list[SentenceInsight] = []
    entities_map: dict[tuple[str, str], dict[str, Any]] = {}
    key_phrases_counter: Counter[str] = Counter()
    total_tokens = 0
    all_lemmas: set[str] = set()
    segment_texts: list[str] = []

    for seg in segments:
        seg_id = int(seg.get("id", 0))
        seg_text = str(seg.get("text", "")).strip()
        start_t = seg.get("start")
        end_t = seg.get("end")

        if not seg_text:
            continue

        segment_texts.append(seg_text)
        doc = nlp(seg_text)

        total_tokens += len(doc)
        if doc.has_annotation("LEMMA"):
            for token in doc:
                if not token.is_punct and not token.is_space and not token.is_stop:
                    all_lemmas.add(token.lemma_.lower())

        for sent in doc.sents:
            sent_str = sent.text.strip()
            if sent_str:
                sentences.append(
                    SentenceInsight(
                        text=sent_str,
                        transcript_segment_id=seg_id,
                        start_time=start_t,
                        end_time=end_t,
                    )
                )

        if doc.has_annotation("ENT_IOB"):
            for ent in doc.ents:
                ent_clean = ent.text.strip()
                if len(ent_clean) > 1 and not ent_clean.isnumeric():
                    key = (ent_clean, ent.label_)
                    if key not in entities_map:
                        entities_map[key] = {
                            "text": ent_clean,
                            "label": ent.label_,
                            "segments": set(),
                            "start_time": start_t,
                            "end_time": end_t,
                        }
                    entities_map[key]["segments"].add(seg_id)
                    if end_t is not None:
                        entities_map[key]["end_time"] = end_t

        if doc.has_annotation("DEP"):
            for chunk in doc.noun_chunks:
                chunk_str = chunk.text.strip().lower()
                if len(chunk_str.split()) > 1 and len(chunk_str) > 4:
                    key_phrases_counter[chunk_str] += 1

    tfidf_results = _extract_tfidf_keywords(segment_texts, top_n=15)
    keywords: list[ExtractedKeyword] = []
    for kw_text, score in tfidf_results:
        matching_seg_ids = [
            int(s.get("id", 0))
            for s in segments
            if re.search(rf"\b{re.escape(kw_text)}\b", str(s.get("text", "")), re.IGNORECASE)
        ]
        keywords.append(
            ExtractedKeyword(
                text=kw_text,
                score=score,
                transcript_segment_ids=matching_seg_ids,
            )
        )

    extracted_entities: list[ExtractedEntity] = []
    entity_counts: dict[str, int] = {}
    for (ent_text, ent_label), data in entities_map.items():
        extracted_entities.append(
            ExtractedEntity(
                text=ent_text,
                label=ent_label,
                transcript_segment_ids=sorted(data["segments"]),
                start_time=data["start_time"],
                end_time=data["end_time"],
            )
        )
        entity_counts[ent_label] = entity_counts.get(ent_label, 0) + 1

    top_key_phrases = [phrase for phrase, _ in key_phrases_counter.most_common(12)]
    topic_keywords = [kw.text for kw in keywords[:6]]

    metadata = LinguisticMetadata(
        total_tokens=total_tokens,
        total_sentences=len(sentences),
        unique_lemmas=len(all_lemmas),
        entity_counts_by_type=entity_counts,
        topic_keywords=topic_keywords,
        nlp_pipeline=pipeline_name,
        capabilities=capabilities,
        warning=warning_msg,
    )

    return TraditionalNLPResult(
        keywords=keywords,
        entities=extracted_entities,
        key_phrases=top_key_phrases,
        sentences=sentences,
        metadata=metadata,
    )
