"""Audio loading, normalisation and chunking helpers (pydub + ffmpeg).

Google's synchronous Speech-to-Text call accepts at most ~60 seconds of audio,
so long recordings are split at natural pauses into chunks of <= 50 seconds.
"""
import io
import shutil

from pydub import AudioSegment
from pydub.silence import split_on_silence

TARGET_RATE = 16000          # 16 kHz is what Google STT works best with
MAX_CHUNK_MS = 50_000        # stay safely below the 60 s sync limit
MIN_CHUNK_MS = 4_000         # merge tiny fragments into their neighbours


class AudioError(Exception):
    """Raised when an audio file cannot be read or is unusable."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def load_audio(path: str) -> AudioSegment:
    """Load any common format and convert to 16 kHz, mono, 16-bit PCM."""
    try:
        audio = AudioSegment.from_file(path)
    except FileNotFoundError:
        raise AudioError(
            "ffmpeg is not installed or not on PATH. Install it to read "
            "MP3/M4A/WebM files (WAV works without it)."
        )
    except Exception as exc:  # pydub raises several different error types
        raise AudioError(
            f"Could not read this audio file ({exc}). Try a WAV, MP3 or M4A file."
        )
    if len(audio) == 0 or audio.rms == 0:
        raise AudioError("The audio is empty or completely silent.")
    return audio.set_frame_rate(TARGET_RATE).set_channels(1).set_sample_width(2)


def split_audio(audio: AudioSegment, max_ms: int = MAX_CHUNK_MS):
    """Split at silences, cap chunk length, and merge very short pieces."""
    parts = split_on_silence(
        audio,
        min_silence_len=700,
        silence_thresh=audio.dBFS - 16,
        keep_silence=300,
    ) or [audio]

    pieces = []
    for part in parts:
        for i in range(0, len(part), max_ms):
            pieces.append(part[i:i + max_ms])

    chunks = []
    for piece in pieces:
        if chunks and len(chunks[-1]) < MIN_CHUNK_MS and len(chunks[-1]) + len(piece) <= max_ms:
            chunks[-1] = chunks[-1] + piece
        else:
            chunks.append(piece)
    return chunks


def to_wav_bytes(segment: AudioSegment) -> bytes:
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()
