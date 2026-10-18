"""Build downloadable TXT and JSON notes."""
import json
import textwrap
from datetime import datetime


def build_notes(transcript: str, analysis: dict, meta: dict = None) -> dict:
    """Combine transcript + analysis + metadata into one structured document."""
    meta = meta or {}
    summary = analysis.get("summary", {})
    return {
        "title": meta.get("title") or "Voice Notes",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": meta.get("source_file"),
        "language": meta.get("language"),
        "speech_engine": meta.get("engine"),
        "transcript": transcript,
        "summary": {
            "text": summary.get("summary", ""),
            "bullets": summary.get("bullets", []),
            "method": summary.get("method", ""),
        },
        "keywords": analysis.get("keywords", []),
        "action_items": analysis.get("action_items", []),
        "stats": analysis.get("stats", {}),
    }


def to_json(notes: dict) -> str:
    return json.dumps(notes, indent=2, ensure_ascii=False)


def _wrap(text: str) -> str:
    return "\n".join(textwrap.fill(p, 88) for p in (text or "").split("\n"))


def to_txt(notes: dict) -> str:
    line = "=" * 64
    out = [line, notes["title"].upper(), line, f"Created : {notes['created_at']}"]
    if notes.get("source_file"):
        out.append(f"Source  : {notes['source_file']}")
    if notes.get("language"):
        out.append(f"Language: {notes['language']}")

    keywords = ", ".join(k["keyword"] for k in notes["keywords"]) or "(none)"
    out += ["", "SUMMARY", "-" * 7, _wrap(notes["summary"]["text"]) or "(none)",
            "", "KEYWORDS", "-" * 8, keywords,
            "", "ACTION ITEMS", "-" * 12]

    if notes["action_items"]:
        for i, item in enumerate(notes["action_items"], 1):
            deadline = item["deadline"] or "-"
            out.append(f"{i}. {item['task']}")
            out.append(f"   Owner: {item['assignee']} | Deadline: {deadline} | "
                       f"Priority: {item['priority']}")
    else:
        out.append("(none detected)")

    out += ["", "FULL TRANSCRIPT", "-" * 15, _wrap(notes["transcript"]), ""]
    return "\n".join(out)
