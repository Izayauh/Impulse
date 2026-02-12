"""
Punctuation restoration module for WhisperLocal.

Uses the oliverguhr/fullstop-punctuation-multilang-large model via
HuggingFace transformers to restore missing punctuation in raw Whisper
transcripts, then applies rule-based sentence capitalization on top.

Existing punctuation that Whisper already got right is preserved —
the model only fills in gaps where punctuation is missing.

Usage:
    from punctuation_restorer import restore_punctuation
    text = restore_punctuation("the quick brown fox jumps over the lazy dog")
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded model singleton — avoids slow startup cost until first call
# ---------------------------------------------------------------------------
_model_instance = None
_model_load_failed = False

_MODEL_NAME = "oliverguhr/fullstop-punctuation-multilang-large"


def _get_model():
    """Return the punctuation NER pipeline, loading it on first use."""
    global _model_instance, _model_load_failed
    if _model_instance is not None:
        return _model_instance
    if _model_load_failed:
        return None

    try:
        import torch
        from transformers import pipeline

        device = 0 if torch.cuda.is_available() else -1
        _model_instance = pipeline(
            "ner",
            model=_MODEL_NAME,
            aggregation_strategy="none",
            device=device,
        )
        logger.info("Punctuation model loaded on %s", "GPU" if device == 0 else "CPU")
        return _model_instance
    except Exception as exc:
        logger.warning("Failed to load punctuation model: %s", exc)
        _model_load_failed = True
        return None


# ---------------------------------------------------------------------------
# Core punctuation prediction (compatible reimplementation)
# ---------------------------------------------------------------------------

def _overlap_chunks(lst: list, n: int, stride: int = 0):
    """Yield successive n-sized chunks with *stride* overlap."""
    for i in range(0, len(lst), n - stride):
        yield lst[i:i + n]


def _predict(pipe, words: list[str]) -> list[tuple[str, str, float]]:
    """Run the NER pipeline on *words* and return (word, label, score) triples."""
    overlap = 5
    chunk_size = 230
    if len(words) <= chunk_size:
        overlap = 0

    batches = list(_overlap_chunks(words, chunk_size, overlap))

    # Drop tiny trailing batch that falls within the overlap window
    if len(batches) > 1 and len(batches[-1]) <= overlap:
        batches.pop()

    tagged: list[tuple[str, str, float]] = []
    for batch in batches:
        # Use last batch completely (no overlap trimming)
        cur_overlap = 0 if batch is batches[-1] else overlap
        text = " ".join(batch)
        result = pipe(text)
        if not result:
            for w in batch[:len(batch) - cur_overlap]:
                tagged.append((w, "0", 0.0))
            continue

        char_index = 0
        result_index = 0
        for word in batch[:len(batch) - cur_overlap]:
            char_index += len(word) + 1
            label = "0"
            score = 0.0
            while result_index < len(result) and char_index > result[result_index]["end"]:
                label = result[result_index]["entity"]
                score = result[result_index]["score"]
                result_index += 1
            tagged.append((word, label, score))

    return tagged


# ---------------------------------------------------------------------------
# Tokenizer that preserves trailing punctuation per word
# ---------------------------------------------------------------------------

# Punctuation marks that the model can predict
_PUNCT_CHARS = set(".,;:!?")

_TRAILING_PUNCT_RE = re.compile(r'^(.*?)([.,;:!?]+)$')


def _tokenize_preserving_punct(text: str) -> list[tuple[str, str]]:
    """Split text into (clean_word, original_trailing_punct) pairs.

    For "Hello, world." this returns:
        [("Hello", ","), ("world", ".")]

    Words without trailing punctuation get an empty string:
        [("the", ""), ("quick", ""), ...]
    """
    tokens: list[tuple[str, str]] = []
    for raw_token in text.split():
        m = _TRAILING_PUNCT_RE.match(raw_token)
        if m and m.group(1):
            tokens.append((m.group(1), m.group(2)))
        else:
            tokens.append((raw_token, ""))
    return tokens


def _merge_predictions(
    tokens: list[tuple[str, str]],
    predictions: list[tuple[str, str, float]],
) -> str:
    """Merge model predictions with original punctuation.

    For each word position:
    - If the original text had punctuation after the word, keep it.
    - Otherwise, use the model's predicted punctuation.
    """
    parts: list[str] = []
    for i, (orig_word, orig_punct) in enumerate(tokens):
        parts.append(orig_word)
        if orig_punct:
            # Preserve existing punctuation from the input
            parts.append(orig_punct + " ")
        elif i < len(predictions):
            _, label, _ = predictions[i]
            if label == "0":
                parts.append(" ")
            elif label in ".,?-:":
                parts.append(label + " ")
            else:
                parts.append(" ")
        else:
            parts.append(" ")
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Rule-based sentence capitalizer
# ---------------------------------------------------------------------------

_SENTENCE_BOUNDARY = re.compile(r'([.!?])\s+')


def _capitalize_sentences(text: str) -> str:
    """Capitalize the first letter of each sentence and the word 'I'."""
    if not text:
        return text

    # Capitalize very first character
    text = text[0].upper() + text[1:]

    # Split on sentence boundaries, capitalize each segment's first letter.
    # The capturing group keeps the punctuation; \s+ is consumed so we
    # must re-insert a space after punctuation when rebuilding.
    segments = _SENTENCE_BOUNDARY.split(text)
    rebuilt: list[str] = []
    for i, seg in enumerate(segments):
        if not seg:
            continue
        if i % 2 == 0:
            # Text segment — capitalize first letter
            seg = seg[0].upper() + seg[1:] if seg else seg
        else:
            # Punctuation segment — re-add the space that the regex consumed
            seg = seg + " "
        rebuilt.append(seg)

    text = "".join(rebuilt).rstrip()

    # Always capitalize standalone "i"
    text = re.sub(r'\bi\b', 'I', text)

    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def restore_punctuation(text: str) -> str:
    """Restore punctuation and sentence capitalization to raw transcript text.

    Runs the fullstop-punctuation-multilang-large NER model to insert
    periods, commas, question marks, etc., then applies rule-based
    sentence capitalization on top.

    Existing punctuation in the input is preserved — the model only fills
    in gaps where punctuation is missing.

    If the model fails to load, falls back to the rule-based capitalizer
    only (no punctuation insertion).

    Args:
        text: Raw transcription text, potentially missing punctuation.

    Returns:
        Text with restored punctuation and proper sentence capitalization.
    """
    if not text or not text.strip():
        return text

    pipe = _get_model()
    if pipe is not None:
        # Tokenize, preserving any existing punctuation per word
        tokens = _tokenize_preserving_punct(text)
        clean_words = [word for word, _ in tokens]
        if clean_words:
            predictions = _predict(pipe, clean_words)
            text = _merge_predictions(tokens, predictions)

    text = _capitalize_sentences(text)
    return text
