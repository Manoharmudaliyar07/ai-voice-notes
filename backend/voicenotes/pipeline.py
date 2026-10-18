"""End-to-end orchestration: audio -> transcript -> NLP analysis."""
from . import action_items, keywords, preprocessing, summarizer
from .transcriber import transcribe_file


def analyze_text(text: str) -> dict:
    """Run preprocessing, summarisation, keyword and action-item extraction."""
    pre = preprocessing.preprocess(text)
    clean = pre["clean_text"]
    return {
        "clean_text": clean,
        "stats": pre["stats"],
        "summary": summarizer.summarize(clean),
        "keywords": keywords.extract_keywords(clean),
        "action_items": action_items.extract_action_items(pre["sentences"]),
    }


def transcribe_and_analyze(path: str, language: str = "en-IN", engine: str = "auto") -> dict:
    t = transcribe_file(path, language, engine)
    return {"transcription": t, "analysis": analyze_text(t["text"])}
