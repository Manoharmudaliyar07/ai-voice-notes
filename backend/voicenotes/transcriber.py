"""Speech-to-text using Google.

Two engines share one interface:

* ``cloud`` - Google Cloud Speech-to-Text API (needs a service-account key,
  returns punctuation and capitalisation).
* ``free``  - the free Google Web Speech API through the SpeechRecognition
  library (this is what the original notebook used; no key needed, but the
  output has no punctuation).

``auto`` picks ``cloud`` when GOOGLE_APPLICATION_CREDENTIALS points to a
valid key file, otherwise ``free``.
"""
import io
import os

import speech_recognition as sr

from .audio_utils import load_audio, split_audio, to_wav_bytes


class TranscriptionError(Exception):
    """Raised for any user-facing transcription failure."""


def cloud_configured() -> bool:
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    return bool(path) and os.path.isfile(path)


def resolve_engine(engine: str = "auto") -> str:
    if engine in ("cloud", "free"):
        return engine
    return "cloud" if cloud_configured() else "free"


def _ensure_sentence(text: str) -> str:
    """Capitalise and terminate a chunk so downstream sentence splitting works."""
    text = text.strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


# --------------------------------------------------------------------------
# Google Cloud Speech-to-Text
# --------------------------------------------------------------------------
def _make_cloud_client():
    if not cloud_configured():
        raise TranscriptionError(
            "Google Cloud credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
            "to your service-account JSON file, or use the free engine."
        )
    from google.cloud import speech
    return speech.SpeechClient()


def _cloud_chunk(client, wav_bytes: bytes, language: str) -> str:
    from google.api_core.exceptions import GoogleAPICallError
    from google.cloud import speech

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        audio_channel_count=1,
        language_code=language,
        enable_automatic_punctuation=True,
    )
    try:
        response = client.recognize(
            config=config, audio=speech.RecognitionAudio(content=wav_bytes)
        )
    except GoogleAPICallError as exc:
        raise TranscriptionError(
            f"Google Cloud Speech-to-Text error: {exc.message}. Check that the "
            "Speech-to-Text API is enabled and billing is active for the project."
        )
    return " ".join(r.alternatives[0].transcript.strip() for r in response.results)


# --------------------------------------------------------------------------
# Free Google Web Speech API (original notebook approach)
# --------------------------------------------------------------------------
def _free_chunk(recognizer: sr.Recognizer, wav_bytes: bytes, language: str) -> str:
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return ""  # nothing intelligible in this chunk
    except sr.RequestError as exc:
        raise TranscriptionError(
            f"Could not reach the Google Speech service ({exc}). Check your internet connection."
        )


# --------------------------------------------------------------------------
def transcribe_file(path: str, language: str = "en-IN", engine: str = "auto") -> dict:
    """Transcribe an audio file of any length and return text + metadata."""
    engine = resolve_engine(engine)
    audio = load_audio(path)
    chunks = split_audio(audio)

    if engine == "cloud":
        client = _make_cloud_client()
        run = lambda wav: _cloud_chunk(client, wav, language)  # noqa: E731
    else:
        recognizer = sr.Recognizer()
        run = lambda wav: _free_chunk(recognizer, wav, language)  # noqa: E731

    texts = []
    for chunk in chunks:
        piece = run(to_wav_bytes(chunk))
        if piece:
            texts.append(_ensure_sentence(piece))

    if not texts:
        raise TranscriptionError(
            "No speech could be recognised. Use a clearer recording and check the language setting."
        )
    return {
        "text": " ".join(texts),
        "engine": engine,
        "language": language,
        "duration_sec": round(len(audio) / 1000, 1),
        "chunks": len(chunks),
    }
