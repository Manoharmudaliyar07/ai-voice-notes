# Viva Notes: AI Voice Notes & Meeting Summarizer

## 30-second pitch
"Meetings and voice notes are long and hard to review. My system converts speech to text with the Google Speech API,
cleans the text with NLP preprocessing, summarises it with a pretrained transformer, extracts keywords with YAKE,
and finds action items with linguistic rules. A React website talks to a Flask backend, and the results can be
downloaded as TXT or JSON."

## Pipeline

```
Audio -> [ffmpeg/pydub: 16 kHz mono, split at pauses] -> Google Speech-to-Text -> transcript
      -> preprocessing -> +-> summariser (DistilBART)   -> summary
                          +-> YAKE / TF-IDF            -> keywords
                          +-> rule-based detector      -> action items
      -> exporter -> TXT / JSON
```

## The main techniques

**1. Speech recognition (ASR).** Google's model converts audio to text. Audio is a waveform, converted to spectral
features; a neural acoustic + language model predicts the most likely words. We send **16 kHz, mono, 16-bit PCM**
because that is the format Google STT handles best. The synchronous API accepts only about 60 seconds, so long
recordings are **split at silences** (pydub `split_on_silence`) into chunks of at most 50 seconds and the texts are joined.
Two engines: the **Cloud API** (official, adds punctuation) and the **free Web Speech API** (what the original notebook used).

**2. Text preprocessing.** Clean the text so later steps work reliably:
* normalise whitespace, remove **filler words** (um, uh, you know) and **repeated words** ("the the");
* **sentence segmentation** (split on . ! ?), capitalise and punctuate;
* **tokenisation**, lower-casing, **stop-word removal** (the, is, of ...) to get meaningful tokens and statistics.

Design choice worth mentioning: stop-words are *not* removed from the text sent to the summariser or action-item rules,
because they need full natural sentences. The stop-word-free tokens are used for statistics and TF-IDF.
Stemming/lemmatisation (running to run) was considered but not needed because YAKE and transformers handle word forms.

**3. Summarisation.** Two families:
* **Extractive:** pick the most important existing sentences (our fallback scores sentences by TF-IDF weight).
* **Abstractive (our main method):** a pretrained **encoder-decoder transformer** (DistilBART fine-tuned on CNN/DailyMail)
  *writes* new sentences. The encoder reads the text with self-attention; the decoder generates the summary word by word using
  **beam search** (4 beams) with a repetition block (`no_repeat_ngram_size=3`).
* Transformers have an input limit (~1024 tokens), so long transcripts use **hierarchical summarisation**: chunk, summarise each chunk, summarise the summaries.
* DistilBART is a **distilled** (smaller, faster) version of BART, trading a little quality for speed. This is **transfer learning**: we reuse a model trained on a huge dataset instead of training our own.

**4. Keyword extraction.**
* **YAKE** (Yet Another Keyword Extractor) is **unsupervised**: it uses only statistics of the single document: capitalisation, word position,
  frequency, how often a word appears in different sentences and its context. **A lower YAKE score means a more important keyword.** No training data or corpus is needed. We show 1 - 2 word phrases and convert the score to a 0 - 100% relevance bar.
* **TF-IDF fallback:** *Term Frequency x Inverse Document Frequency*. A word is important if it is frequent here but rare elsewhere.
  With only one transcript there is no "elsewhere", so we treat **each sentence as a document**.

**5. Action-item identification (rule-based NLP).** Each sentence gets an evidence score:

| Evidence | Points | Example |
|---|---|---|
| Strong obligation cue | +2 | "need to", "must", "please", "let's", "follow up" |
| Weak cue | +1 | "will", "should", "going to", "can you" |
| Action verb | +1 | send, prepare, schedule, fix, review |
| Responsible person | +1 | a name, or I / we / you |
| Deadline phrase (regex) | +1 | "by Friday", "tomorrow", "end of the day", "25th October" |

Score >= 3 means an action item. We also extract **owner**, **deadline**, and **priority** (urgent, asap), and give a confidence
(score / 5). Example: *"Priya will send the mockups by Friday"* = will (+1) + send (+1) + Priya (+1) + Friday (+1) = 4.
"It will rain tomorrow" scores only 2, so it is correctly rejected.

## Likely viva questions

**Why rules instead of a machine-learning classifier for action items?** There is no free labelled meeting dataset; rules need no
training data, are fully explainable, and work well on commitment language. A future upgrade is fine-tuning a classifier or using zero-shot classification.

**Why pretrained models?** Training ASR or a summariser needs huge data and compute. Pretrained models give state-of-the-art quality immediately (transfer learning).

**Abstractive vs extractive?** Extractive copies sentences (safe, but choppy); abstractive rewrites (fluent and shorter) but can occasionally paraphrase imperfectly.

**What is WER?** Word Error Rate = (substitutions + deletions + insertions) / words in the reference. It is the standard ASR metric.

**What are the limitations?** Accents and noise reduce ASR accuracy; the free API has no punctuation; the first transformer run is slow;
names are only detected when capitalised (the Cloud API does this well); rules miss unusual phrasing; no speaker diarisation (who said what).

**Future work:** speaker diarisation, real-time streaming transcription, Named Entity Recognition for owners, a fine-tuned action-item classifier, multi-language summaries, saving notes in a database.

**Why Flask + React?** Flask keeps the Python NLP in one lightweight REST API; React gives a responsive interactive UI. They are decoupled and talk through JSON.

**What did you fix in the original notebook?** (1) The microphone code both defined and called the recorder, so it recorded twice, and saved WebM data as `.wav`, so ffmpeg failed. (2) The Streamlit/localtunnel launch never worked (`streamlit` not on PATH, `npx` waiting for a prompt). (3) The extension section was unfinished. These were replaced with tested modules and the React + Flask app.

## Honest limitations to state if asked
* The action-item detector is heuristic, not a trained model: expect some false positives/negatives.
* Summary quality depends on the transcript quality; the free engine's missing punctuation lowers it.
