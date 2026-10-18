# AI Voice Notes & Meeting Summarizer

**Project title: Speech Recognition in Python using Google Speech API**

Upload or record audio, get a transcript, then automatically get a summary, keywords and
meeting action items. Download everything as TXT or JSON.

## Folder structure

```
ai-voice-notes/
├── README.md
├── docs/VIVA_NOTES.md              # presentation / viva preparation
├── notebook/
│   └── NLP_miniProject_Improved.ipynb   # your Colab notebook, fixed and extended
├── backend/                        # Flask API (Python)
│   ├── app.py                      # routes: /api/health, /transcribe, /analyze, /export/<txt|json>
│   ├── requirements.txt
│   ├── .env.example                # copy to .env
│   ├── credentials/                # put google-key.json here (git-ignored)
│   └── voicenotes/                 # reusable NLP package (no Flask inside)
│       ├── audio_utils.py          # load any audio format, 16 kHz mono, split at pauses
│       ├── transcriber.py          # Google Cloud STT + free Google Web Speech engine
│       ├── preprocessing.py        # cleaning, tokenising, stop-word removal, statistics
│       ├── summarizer.py           # DistilBART summariser + extractive fallback
│       ├── keywords.py             # YAKE + TF-IDF fallback
│       ├── action_items.py         # rule-based action-item detector
│       ├── exporter.py             # TXT and JSON notes
│       └── pipeline.py             # audio -> transcript -> analysis
└── frontend/                       # React (Vite)
    ├── package.json, vite.config.js, index.html
    └── src/
        ├── main.jsx, App.jsx, api.js, styles.css
        └── components/ AudioInput.jsx, Results.jsx, Feedback.jsx
```

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.9 to 3.13 | `python --version` |
| Node.js | 18 or newer | `node --version` |
| ffmpeg | any recent | `ffmpeg -version` |

Install ffmpeg: **Windows** `winget install Gyan.FFmpeg` (restart the terminal) · **macOS** `brew install ffmpeg` ·
**Ubuntu** `sudo apt install ffmpeg`. ffmpeg is needed for MP3/M4A/WebM and for microphone recordings; plain WAV works without it.

## Run the backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # Windows: copy .env.example .env
python app.py
```

The API now runs on **http://127.0.0.1:5000** (check `http://127.0.0.1:5000/api/health`).

* The **first** summarisation downloads the DistilBART model (~1.2 GB, once) and takes a minute to load.
  Set `PRELOAD_MODEL=1` in `.env` to load it at start-up instead.
* Want to start instantly with no download? Set `SUMMARIZER=extractive` in `.env`.
* If the model cannot be downloaded, the app falls back to extractive summarisation and tells the user.
* To avoid a huge `torch` download, remove `torch`, `transformers`, `sentencepiece` from `requirements.txt`
  and use `SUMMARIZER=extractive`.

## Run the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to Flask, so nothing else is needed.

## Quick demo checklist

1. Open the site. The badge top-right should say *Engine: ...* (backend online).
2. Select **Use sample meeting text** then **Analyze text**. All three tabs fill in. (Works with no audio and no internet for the NLP part.)
3. Upload a WAV/MP3, or select **Record voice note**, then **Transcribe audio**.
4. Edit the transcript if needed and re-run **Analyze text**.
5. Use **Download TXT / JSON**.

Tip for a voice demo: say full sentences with pauses, for example *"Priya will send the report by Friday. We need to fix the login bug before the release."*

## Google API setup

The project supports two speech engines. `auto` mode picks Cloud when a key is configured, otherwise the free one.

### Option 1: Free Google Web Speech API (no setup)
This is what your original notebook used (`recognizer.recognize_google`). It needs only an internet connection.
Limits: unofficial, rate-limited, **no punctuation** in the output. Good enough for a demo.

### Option 2: Google Cloud Speech-to-Text API (recommended for the final demo)
Official API, returns **punctuation and capitalisation**, which improves summaries and action items.

1. Go to <https://console.cloud.google.com> and sign in.
2. **Create a project** (top bar, project picker, *New Project*), for example `voice-notes`.
3. **Enable billing** (Billing menu). New accounts get free credits, and Speech-to-Text includes a free monthly tier (60 minutes at the time of writing; check current pricing). A mini-project demo costs essentially nothing.
4. **Enable the API:** *APIs & Services, Library*, search **Cloud Speech-to-Text API**, select **Enable**.
5. **Create a service account:** *IAM & Admin, Service Accounts, Create service account*, name it `voice-notes-sa`. Role: **Cloud Speech Client** (or *Editor* for a quick test). Finish.
6. **Create a key:** open the service account, *Keys, Add key, Create new key, JSON*. A `.json` file downloads.
7. Move the file to `backend/credentials/google-key.json`.
8. In `backend/.env` set `GOOGLE_APPLICATION_CREDENTIALS=credentials/google-key.json`.
9. Restart `python app.py`. The website badge now shows **Engine: Google Cloud Speech-to-Text**.

Security: never commit or share the key (`.gitignore` already excludes it). Delete the key and the project after your demo if you like.

Common errors: *403 / PERMISSION_DENIED* means the API is not enabled or billing is off. *DefaultCredentialsError* means the path in `.env` is wrong.

## API reference

| Method | Route | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | none | engine, ffmpeg and summariser status |
| POST | `/api/transcribe` | multipart: `audio`, `language` | `{text, engine, duration_sec, chunks}` |
| POST | `/api/analyze` | `{"text": "..."}` | `{clean_text, stats, summary, keywords, action_items}` |
| POST | `/api/export/txt` or `/json` | `{transcript, analysis, meta}` | file download |

## Notebook

Upload `notebook/NLP_miniProject_Improved.ipynb` to Google Colab and run top to bottom. Part C regenerates the same
`voicenotes` package used by the backend. In Colab the microphone cell needs browser mic permission; if it is blocked,
the rest still works with an uploaded file.

## Troubleshooting

| Problem | Fix |
|---|---|
| Badge says *Backend offline* | Start `python app.py` in `backend/` and refresh |
| *ffmpeg is not installed* | Install ffmpeg and reopen the terminal |
| *Could not reach the Google Speech service* | Check internet; the free engine needs access to Google |
| *No speech could be recognised* | Use a clearer, louder clip; check the language dropdown |
| Summary shows an amber notice | The model could not load, so the extractive fallback was used |
| Microphone blocked | Allow it in the browser address bar (works on `localhost`), or upload a file |
| `pip` fails on `torch` | Use the extractive mode (see above) |
