import { useEffect, useRef, useState } from "react";

const formatTime = (s) =>
  `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

// Lets the user either upload an audio file or record from the microphone.
// Calls onChange(File | null) whenever the chosen audio changes.
export default function AudioInput({ file, onChange, disabled }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [localError, setLocalError] = useState("");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dragging, setDragging] = useState(false);

  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const inputRef = useRef(null);

  // Build (and clean up) an object URL for the audio preview player.
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Stop the microphone if the component unmounts mid-recording.
  useEffect(
    () => () => {
      clearInterval(timerRef.current);
      recorderRef.current?.stream?.getTracks().forEach((t) => t.stop());
    },
    []
  );

  const pickFile = (f) => {
    if (!f) return;
    setLocalError("");
    if (!f.type.startsWith("audio/") && !/\.(wav|mp3|m4a|flac|ogg|webm|aac|opus)$/i.test(f.name)) {
      setLocalError("Please choose an audio file (WAV, MP3, M4A, FLAC, OGG or WebM).");
      return;
    }
    onChange(f);
  };

  const startRecording = async () => {
    setLocalError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setLocalError("Recording is not supported in this browser. Upload an audio file instead.");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setLocalError(
        "Microphone access was blocked. Allow it from the address bar, or upload a file instead."
      );
      return;
    }
    const chunks = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const type = recorder.mimeType || "audio/webm";
      const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
      onChange(new File([new Blob(chunks, { type })], `recording.${ext}`, { type }));
    };
    recorder.start();
    recorderRef.current = recorder;
    setSeconds(0);
    setRecording(true);
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
  };

  const stopRecording = () => {
    clearInterval(timerRef.current);
    recorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <div>
      <div
        className={`dropzone${dragging ? " dragging" : ""}${disabled ? " disabled" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) pickFile(e.dataTransfer.files?.[0]);
        }}
      >
        <p className="dropzone-title">Drop an audio file here</p>
        <p className="muted">WAV, MP3, M4A, FLAC, OGG or WebM, up to 25 MB</p>
        <div className="row">
          <button
            className="btn btn-secondary"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || recording}
          >
            Choose file
          </button>
          {!recording ? (
            <button className="btn btn-secondary" onClick={startRecording} disabled={disabled}>
              Record voice note
            </button>
          ) : (
            <button className="btn btn-danger" onClick={stopRecording}>
              <span className="rec-dot" aria-hidden="true" />
              Stop recording {formatTime(seconds)}
            </button>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg,.webm,.aac,.opus"
          hidden
          onChange={(e) => {
            pickFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>

      {localError && (
        <p className="field-error" role="alert">
          {localError}
        </p>
      )}

      {file && previewUrl && (
        <div className="audio-preview">
          <div className="audio-meta">
            <strong title={file.name}>{file.name}</strong>
            <span className="muted">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
            <button
              className="link-btn"
              onClick={() => onChange(null)}
              disabled={disabled || recording}
            >
              Remove
            </button>
          </div>
          <audio controls src={previewUrl} />
        </div>
      )}
    </div>
  );
}
