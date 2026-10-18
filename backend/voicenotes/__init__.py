"""voicenotes - reusable NLP modules for the AI Voice Notes & Meeting Summarizer.

The package has no Flask dependency, so the same code runs in the Flask API
and in the Google Colab notebook.
"""
from .pipeline import analyze_text, transcribe_and_analyze  # noqa: F401
