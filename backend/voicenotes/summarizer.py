"""Automatic summarisation.

Primary method: abstractive summarisation with a pretrained transformer
(default: DistilBART trained on CNN/DailyMail). Long transcripts are handled
hierarchically: split into chunks -> summarise each -> summarise the summaries.

Fallback: extractive summarisation (TF-IDF sentence scoring) which needs no
model download. Used automatically if the transformer cannot be loaded.
"""
import logging
import math
import os

from sklearn.feature_extraction.text import TfidfVectorizer

from .preprocessing import split_sentences

log = logging.getLogger(__name__)
DEFAULT_MODEL = "sshleifer/distilbart-cnn-12-6"
CHUNK_WORDS = 450          # ~600-700 tokens, safely inside a 1024-token window
_cache = {}


def _load_model():
    if "model" not in _cache:
        import torch  # noqa: F401  (fail early if torch is missing)
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        name = os.getenv("SUMMARY_MODEL", DEFAULT_MODEL)
        log.info("Loading summarisation model %s ...", name)
        _cache["name"] = name
        _cache["tok"] = AutoTokenizer.from_pretrained(name)
        _cache["model"] = AutoModelForSeq2SeqLM.from_pretrained(name).eval()
    return _cache["tok"], _cache["model"], _cache["name"]


def preload():
    """Optional: call at start-up so the first request is not slow."""
    try:
        _load_model()
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not preload summariser: %s", exc)


def _generate(text: str) -> str:
    import torch

    tok, model, name = _load_model()
    n_words = len(text.split())
    max_len = min(130, max(30, int(n_words * 0.5)))
    min_len = max(10, min(max_len - 5, int(n_words * 0.15)))
    prompt = "summarize: " + text if "t5" in name.lower() else text
    inputs = tok(prompt, return_tensors="pt", truncation=True,
                 max_length=min(getattr(tok, "model_max_length", 1024), 1024))
    with torch.no_grad():
        ids = model.generate(
            **inputs, num_beams=4, max_length=max_len, min_length=min_len,
            no_repeat_ngram_size=3, length_penalty=2.0, early_stopping=True,
        )
    return tok.decode(ids[0], skip_special_tokens=True).strip()


def _chunk_sentences(sentences, limit=CHUNK_WORDS):
    chunks, current, count = [], [], 0
    for s in sentences:
        w = len(s.split())
        if current and count + w > limit:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(s)
        count += w
    if current:
        chunks.append(" ".join(current))
    return chunks


def abstractive_summary(text: str) -> str:
    chunks = _chunk_sentences(split_sentences(text))
    partial = [_generate(c) for c in chunks]
    combined = " ".join(partial)
    if len(chunks) > 1 and len(combined.split()) > 150:   # second pass
        return _generate(combined)
    return combined


def extractive_summary(text: str, max_sentences: int = 4) -> str:
    sentences = split_sentences(text)
    if len(sentences) <= 2:
        return text
    k = max(2, min(max_sentences, round(len(sentences) * 0.25)))
    try:
        tfidf = TfidfVectorizer(stop_words="english").fit_transform(sentences)
    except ValueError:                                     # only stop-words
        return " ".join(sentences[:k])
    # Sum of TF-IDF weights, damped by length so long sentences don't always win
    scores = [tfidf[i].sum() / math.sqrt(len(sentences[i].split()) or 1)
              for i in range(len(sentences))]
    top = sorted(sorted(range(len(sentences)), key=lambda i: -scores[i])[:k])
    return " ".join(sentences[i] for i in top)


def summarize(text: str) -> dict:
    """Return {summary, bullets, method, warning}."""
    words = len(text.split())
    mode = os.getenv("SUMMARIZER", "auto").lower()   # auto | abstractive | extractive
    warning = None

    if words < 30:
        summary, method = text, "passthrough (text is already short)"
    elif mode == "extractive":
        summary, method = extractive_summary(text), "extractive (TF-IDF sentence scoring)"
    else:
        try:
            summary = abstractive_summary(text)
            method = f"abstractive ({_cache.get('name', DEFAULT_MODEL)})"
        except Exception as exc:  # noqa: BLE001
            if mode == "abstractive":
                raise
            log.warning("Abstractive summariser unavailable: %s", exc)
            summary, method = extractive_summary(text), "extractive (TF-IDF sentence scoring)"
            warning = ("The pretrained summarisation model could not be loaded, so a "
                       "lighter extractive summary was used instead.")
    return {"summary": summary, "bullets": split_sentences(summary),
            "method": method, "warning": warning}
