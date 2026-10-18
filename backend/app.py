"""Flask API for the AI Voice Notes & Meeting Summarizer."""
import logging
import os
import tempfile
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Allow a relative key path in .env (relative to the backend folder)
_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _cred and not os.path.isabs(_cred):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str((BASE_DIR / _cred).resolve())

from voicenotes import analyze_text, summarizer  # noqa: E402
from voicenotes.audio_utils import AudioError, ffmpeg_available  # noqa: E402
from voicenotes.exporter import build_notes, to_json, to_txt  # noqa: E402
from voicenotes.transcriber import (TranscriptionError, cloud_configured,  # noqa: E402
                                    resolve_engine, transcribe_file)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("voicenotes")

ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aac", ".mp4", ".opus"}
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
MAX_TEXT_CHARS = 60_000

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024
CORS(app)  # lets the Vite dev server (port 5173) call this API directly if needed

if os.getenv("PRELOAD_MODEL", "0") == "1":
    threading.Thread(target=summarizer.preload, daemon=True).start()


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "speech_engine": resolve_engine("auto"),
        "cloud_configured": cloud_configured(),
        "ffmpeg": ffmpeg_available(),
        "summarizer_mode": os.getenv("SUMMARIZER", "auto"),
        "max_upload_mb": MAX_MB,
    })


@app.post("/api/transcribe")
def transcribe():
    file = request.files.get("audio")
    if file is None or not file.filename:
        return error("No audio file received. Choose or record an audio clip first.")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return error(f"Unsupported file type '{ext or "unknown"}'. Use WAV, MP3, M4A, FLAC, OGG or WebM.")

    language = request.form.get("language", "en-IN")
    engine = request.form.get("engine", "auto")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp.name)
        path = tmp.name
    try:
        result = transcribe_file(path, language, engine)
        return jsonify(result)
    except (TranscriptionError, AudioError) as exc:
        return error(str(exc), 422)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if len(text.split()) < 5:
        return error("Text is too short to analyse. Enter at least a few sentences.")
    if len(text) > MAX_TEXT_CHARS:
        return error("Text is too long. Please keep it under 60,000 characters.", 413)
    return jsonify(analyze_text(text))


@app.post("/api/export/<fmt>")
def export(fmt):
    if fmt not in ("txt", "json"):
        return error("Export format must be txt or json.", 404)
    data = request.get_json(silent=True) or {}
    transcript = data.get("transcript", "")
    analysis = data.get("analysis")
    if not transcript or not analysis:
        return error("Nothing to export yet. Transcribe or analyse some text first.")
    notes = build_notes(transcript, analysis, data.get("meta"))
    body, mime = (to_json(notes), "application/json") if fmt == "json" else (to_txt(notes), "text/plain")
    return Response(body, mimetype=mime + "; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=voice-notes.{fmt}"})


@app.errorhandler(HTTPException)
def http_error(exc):
    if exc.code == 413:
        return error(f"File is too large. The limit is {MAX_MB} MB.", 413)
    return error(exc.description or "Request failed.", exc.code or 500)


@app.errorhandler(Exception)
def unexpected(exc):
    log.exception("Unhandled error")
    return error("Something went wrong on the server. Check the backend terminal for details.", 500)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
