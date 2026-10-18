import { useEffect, useState } from "react";
import { analyzeText, downloadNotes, getHealth, transcribeAudio } from "./api.js";
import AudioInput from "./components/AudioInput.jsx";
import { ErrorBanner, Spinner } from "./components/Feedback.jsx";
import Results from "./components/Results.jsx";

const LANGUAGES = [
  { code: "en-IN", label: "English (India)" },
  { code: "en-US", label: "English (US)" },
  { code: "en-GB", label: "English (UK)" },
  { code: "hi-IN", label: "Hindi" },
];

const SAMPLE_TEXT =
  "Welcome everyone to the weekly project sync. The website redesign is almost done and the design team " +
  "has finished the new landing page and the checkout flow. Priya will send the final mockups to the client by Friday. " +
  "We need to fix the login bug before the release because it is blocking the testers. " +
  "Rahul should prepare the demo slides for the review meeting next week. " +
  "The marketing budget for the quarter was approved and the campaign will launch in November. " +
  "Please schedule a follow up call with the vendor tomorrow. " +
  "I'll update the project documentation by end of the day. " +
  "The server migration went smoothly and performance improved by thirty percent. " +
  "Let's finalize the pricing proposal on 25th October.";

const ENGINE_LABELS = {
  cloud: "Google Cloud Speech-to-Text",
  free: "Google Web Speech API (free)",
};

export default function App() {
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("en-IN");
  const [transcript, setTranscript] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(null); // null | "transcribe" | "analyze"
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("summary");
  const [engineUsed, setEngineUsed] = useState(null);
  const [health, setHealth] = useState({ state: "checking" });

  useEffect(() => {
    getHealth()
      .then((h) => setHealth({ state: "online", ...h }))
      .catch(() => setHealth({ state: "offline" }));
  }, []);

  const runAnalysis = async (text) => {
    setBusy("analyze");
    try {
      setAnalysis(await analyzeText(text));
      setTab("summary");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const handleTranscribe = async () => {
    if (!file) return;
    setError("");
    setAnalysis(null);
    setBusy("transcribe");
    let text;
    try {
      const result = await transcribeAudio(file, language);
      text = result.text;
      setTranscript(text);
      setEngineUsed(result.engine);
    } catch (e) {
      setError(e.message);
      setBusy(null);
      return;
    }
    await runAnalysis(text);
  };

  const handleAnalyze = async () => {
    setError("");
    await runAnalysis(transcript);
  };

  const handleDownload = async (format) => {
    setDownloading(format);
    try {
      await downloadNotes(format, {
        transcript,
        analysis,
        meta: {
          title: file ? `Notes: ${file.name}` : "Voice Notes",
          source_file: file?.name || null,
          language,
          engine: engineUsed,
        },
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloading(null);
    }
  };

  const loadSample = () => {
    setError("");
    setAnalysis(null);
    setTranscript(SAMPLE_TEXT);
  };

  const working = busy !== null;
  const canAnalyze = transcript.trim().split(/\s+/).filter(Boolean).length >= 5;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>AI Voice Notes &amp; Meeting Summarizer</h1>
          <p className="subtitle">Speech Recognition in Python using Google Speech API</p>
        </div>
        <span className={`status status-${health.state}`}>
          {health.state === "checking" && "Checking backend..."}
          {health.state === "offline" && "Backend offline"}
          {health.state === "online" &&
            (health.ffmpeg
              ? `Engine: ${ENGINE_LABELS[health.speech_engine]}`
              : "ffmpeg missing: only WAV supported")}
        </span>
      </header>

      <ErrorBanner message={error} onDismiss={() => setError("")} />
      {health.state === "offline" && (
        <ErrorBanner message="The backend is not reachable. Start the Flask server (python app.py) and refresh this page." />
      )}

      <main className="workspace">
        <div className="column">
          <section className="panel" aria-labelledby="input-heading">
            <div className="panel-head">
              <h2 id="input-heading">1. Add audio</h2>
              <label className="select-wrap">
                <span className="muted">Language</span>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  disabled={working}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <AudioInput file={file} onChange={setFile} disabled={working} />
            <button
              className="btn btn-primary btn-block"
              onClick={handleTranscribe}
              disabled={!file || working}
            >
              {busy === "transcribe" ? (
                <Spinner label="Transcribing with Google Speech..." />
              ) : (
                "Transcribe audio"
              )}
            </button>
          </section>

          <section className="panel" aria-labelledby="transcript-heading">
            <div className="panel-head">
              <h2 id="transcript-heading">2. Transcript</h2>
              <button className="link-btn" onClick={loadSample} disabled={working}>
                Use sample meeting text
              </button>
            </div>
            <textarea
              className="transcript"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Your transcript appears here. You can edit it to fix recognition mistakes, or paste any meeting text, then analyze it."
              rows={11}
              disabled={busy === "transcribe"}
              aria-label="Transcript"
            />
            <div className="row row-between">
              <span className="muted small">
                {engineUsed
                  ? `Transcribed with ${ENGINE_LABELS[engineUsed]}. Edit the text and re-run if needed.`
                  : "Editable. Analysis uses exactly what is shown here."}
              </span>
              <button
                className="btn btn-secondary"
                onClick={handleAnalyze}
                disabled={!canAnalyze || working}
              >
                {busy === "analyze" ? "Analyzing..." : "Analyze text"}
              </button>
            </div>
          </section>
        </div>

        <div className="column">
          <Results
            analysis={analysis}
            tab={tab}
            onTabChange={setTab}
            loading={busy === "analyze"}
            onDownload={handleDownload}
            downloading={downloading}
          />
        </div>
      </main>

      <footer className="app-footer">
        NLP mini-project: Google Speech-to-Text, text preprocessing, transformer summarisation,
        YAKE keywords and rule-based action items.
      </footer>
    </div>
  );
}
