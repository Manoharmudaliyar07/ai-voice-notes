"""Keyword extraction with YAKE (primary) and TF-IDF (fallback)."""
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .preprocessing import split_sentences


def _yake_keywords(text: str, top_n: int):
    import yake

    extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.7, top=top_n * 2)
    raw = extractor.extract_keywords(text)
    pairs = []
    for a, b in raw:                                   # tolerate (kw, score) or (score, kw)
        kw, score = (a, b) if isinstance(a, str) else (b, a)
        pairs.append((kw.lower().strip(), float(score)))
    return pairs                                       # YAKE: LOWER score = MORE relevant


def _tfidf_keywords(text: str, top_n: int):
    """Treat each sentence as a document so IDF is meaningful for one transcript."""
    docs = split_sentences(text) or [text]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform(docs)
    weights = matrix.sum(axis=0).A1
    terms = vec.get_feature_names_out()
    ranked = sorted(zip(terms, weights), key=lambda x: -x[1])[: top_n * 2]
    top = ranked[0][1] if ranked else 1
    return [(t, 1 - (w / top) * 0.8) for t, w in ranked]  # convert to "lower = better"


_TIME_WORDS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
               "today", "tomorrow", "tonight", "yesterday", "week", "weekly", "next", "asap"}


def _keep(kw: str) -> bool:
    words = re.findall(r"[a-z]+", kw)
    return (len(kw) > 2 and bool(words)
            and not all(w in ENGLISH_STOP_WORDS or w in _TIME_WORDS for w in words))


def extract_keywords(text: str, top_n: int = 10, method: str = "yake") -> list:
    """Return [{keyword, relevance (0-1, higher = better), method}]."""
    used, pairs = method, []
    if method == "yake":
        try:
            pairs = _yake_keywords(text, top_n)
        except Exception:  # noqa: BLE001  (yake missing or failed)
            pairs = []
        if not pairs:
            used = "tfidf"
    if used == "tfidf" or not pairs:
        used = "tfidf"
        try:
            pairs = _tfidf_keywords(text, top_n)
        except ValueError:
            return []

    # remove near-duplicates (a unigram contained in an already chosen phrase)
    chosen = []
    for kw, score in sorted(pairs, key=lambda p: p[1]):
        if _keep(kw) and not any(kw in c[0].split() or kw == c[0] for c in chosen):
            chosen.append((kw, score))
        if len(chosen) == top_n:
            break
    if not chosen:
        return []

    lo, hi = min(s for _, s in chosen), max(s for _, s in chosen)
    out = []
    for kw, s in chosen:
        rel = 1.0 if hi == lo else 1 - ((s - lo) / (hi - lo)) * 0.8
        out.append({"keyword": kw, "relevance": round(rel, 2), "method": used})
    return out
