"""NLP text preprocessing.

Two views of the text are produced:

* ``clean_text``  - light cleaning that keeps natural sentences. Summarisation
  and action-item rules need real sentences, so stop-words are NOT removed here.
* ``tokens``      - lower-cased, punctuation-free, stop-word-free tokens used
  for statistics (and by the TF-IDF keyword fallback).
"""
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

FILLERS = re.compile(
    r"\b(?:u+m+|u+h+|e+r+m*|h+m+|a+h+|you know|i mean|kind of like)\b[,]?\s*",
    re.IGNORECASE,
)
REPEATED_WORD = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
TOKEN = re.compile(r"[a-z]+(?:'[a-z]+)?")


def split_sentences(text: str) -> list:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def clean_text(text: str) -> tuple:
    """Return (clean_text, number_of_filler_words_removed)."""
    text = re.sub(r"\s+", " ", text).strip()
    text, n_fill = FILLERS.subn("", text)
    text = REPEATED_WORD.sub(r"\1", text)                 # "the the" -> "the"
    text = re.sub(r"\s+([,.!?])", r"\1", text)             # no space before punctuation
    text = re.sub(r"\s+", " ", text).strip()

    sentences = split_sentences(text)
    fixed = []
    for s in sentences:
        s = s[0].upper() + s[1:]                           # capitalise
        if s[-1] not in ".!?":
            s += "."                                       # terminate
        fixed.append(s)
    return " ".join(fixed), n_fill


def tokenize(text: str, remove_stopwords: bool = True) -> list:
    tokens = TOKEN.findall(text.lower())
    if remove_stopwords:
        tokens = [t for t in tokens if t not in ENGLISH_STOP_WORDS and len(t) > 2]
    return tokens


def preprocess(text: str) -> dict:
    cleaned, n_fill = clean_text(text)
    sentences = split_sentences(cleaned)
    all_tokens = tokenize(cleaned, remove_stopwords=False)
    tokens = tokenize(cleaned)
    return {
        "clean_text": cleaned,
        "sentences": sentences,
        "tokens": tokens,
        "stats": {
            "words": len(all_tokens),
            "sentences": len(sentences),
            "fillers_removed": n_fill,
            "tokens_after_stopwords": len(tokens),
            "unique_terms": len(set(tokens)),
        },
    }
