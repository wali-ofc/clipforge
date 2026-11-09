# ClipForge

Local-first AI video clipping. Long recordings go in; short vertical clips come out — processed entirely on your machine, with no cloud services and no accounts.

> **Build status: Phase 0 + Phase 1 + Phase 2 + Phase 3 complete.**
> Uploads are streamed to disk, validated with `ffprobe`, persisted in SQLite, and processed by a single background worker. The worker extracts audio with FFmpeg, transcribes it locally with faster-whisper, then asks a local Ollama model for self-contained candidate moments. Proposals are validated, boundary-refined, scored, deduplicated, and stored. Speaker tracking, captions, and 9:16 rendering are **not implemented yet**.

## What works today

- Typed configuration from `.env` files and environment variables
- Health endpoint reporting database, `ffmpeg`, `ffprobe`, faster-whisper, and Ollama availability
- Streamed, chunked uploads written straight to disk (never buffered fully in memory)
- Immediate `ffprobe` validation: extension, size, readability, video stream, duration, codec
- Persistent jobs in SQLite with monotonic progress and stage messages
- Single worker that claims the oldest queued job and recovers interrupted jobs on startup
- Local CPU/INT8 transcription with faster-whisper, including word-level timestamps
- Graceful handling of silent audio and videos with no audio stream (empty transcript, job still completes)
- Overlapping transcript windows (about three minutes) so the LLM never receives the whole transcript at once
- Structured JSON clip proposals through Ollama, validated and boundary-refined against word and segment timestamps
- Deterministic weighted **clip potential** scores, duplicate removal, and a configurable result limit
- Minimal Next.js UI: drag/drop upload, upload progress, live job status polling, transcript summary, candidate clip cards, error states
- Metadata, transcript, and clip proposals exposed over the API; rendered clip files are not produced yet

Captions are intentionally **not** generated or burned into any video. The transcript is internal pipeline data.

## Repository layout

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── api/          # health, upload, job/transcript, clip routes + helpers
│   │   ├── models/       # SQLAlchemy Job and Clip models
│   │   ├── prompts/      # editable clip-selection prompt
│   │   ├── schemas/      # Pydantic response, transcript, and LLM models
│   │   ├── services/     # probing, tool checks, transcription, Ollama, selection
│   │   ├── utils/        # config-independent helpers (files, paths, subprocess)
│   │   ├── worker/       # queue runner and inspection/transcription/selection pipeline
│   │   ├── config.py     # typed settings
│   │   ├── db.py         # engine, sessions, schema creation + additive migrations
│   │   └── main.py       # FastAPI app + lifespan
│   ├── tests/            # 95 pytest tests
│   ├── data/             # runtime only, gitignored
│   ├── requirements.lock.txt
│   ├── pyproject.toml
│   └── .env              # local machine overrides, gitignored
├── frontend/
│   ├── src/app/          # landing page, /jobs/[id], 404
│   ├── src/components/   # upload form, status view, icons, chrome
│   ├── src/lib/          # API client, formatting helpers
│   └── .env.local.example
├── .env.example
└── .gitignore
```

## Prerequisites

| Tool | Version used | Notes |
| --- | --- | --- |
| Python | 3.11.x | Backend requires `>=3.11,<3.12` |
| Node.js | 20+ (26 used) | Frontend build |
| FFmpeg / ffprobe | 9.0.2 | Must be on `PATH` or set `FFMPEG_BIN` / `FFPROBE_BIN` |
| Ollama | 0.40+ | Local LLM server for clip selection |
| Whisper model | downloaded on first use | Cached under `backend/data/models` |

## Setup

### Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If `ffmpeg` / `ffprobe` are not on `PATH`, create `backend/.env`:

```dotenv
FFMPEG_BIN=C:/ffmpeg-9.0.2-essentials_build/bin/ffmpeg.exe
FFPROBE_BIN=C:/ffmpeg-9.0.2-essentials_build/bin/ffprobe.exe
```

A locked, fully resolved dependency list lives in `backend/requirements.lock.txt`.

The first transcription downloads the configured Whisper model into `WHISPER_MODEL_DIR` (default `backend/data/models`). This needs internet access once; later runs work offline. For a fast smoke test, set `WHISPER_MODEL=tiny`. The default is `small`, which is larger and slower on CPU.

### Ollama (Phase 3)

Install [Ollama](https://ollama.com/) and start it:

```powershell
ollama serve
```

Pull the configured model in another terminal:

```powershell
ollama pull qwen2.5:3b
```

`qwen2.5:3b` is the default because it fits comfortably on a 16 GB machine. Any installed chat model can be used by setting `OLLAMA_MODEL`; the health endpoint and job errors report when the configured model is missing. Clip selection fails with an actionable message if Ollama is unreachable or the model is not installed.

### Frontend

```powershell
cd frontend
npm.cmd install
Copy-Item .env.local.example .env.local
```

## Running

Two processes, two terminals.

```powershell
# Terminal 1 — API + background worker
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2 — UI
cd frontend
npm.cmd run dev
```

- UI: <http://127.0.0.1:3000>
- API: <http://127.0.0.1:8000>
- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

The worker starts automatically with the API (`WORKER_AUTOSTART=true`). Jobs left in an active state by a crashed process are marked `failed` on the next startup rather than being silently retried.

## Configuration

Defaults live in `.env.example`. Values are resolved in this order (later wins):

1. project-root `.env`
2. `backend/.env`
3. real environment variables

Relative paths resolve against `backend/`, not the current shell directory.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Environment label |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind address reference |
| `DATA_DIR` | `./data` | Uploads, work files, clips, SQLite |
| `DATABASE_URL` | `sqlite:///./data/clipforge.db` | SQLAlchemy URL |
| `MAX_UPLOAD_BYTES` | `5368709120` (5 GiB) | Hard upload limit |
| `UPLOAD_CHUNK_BYTES` | `1048576` | Streaming copy chunk size |
| `ALLOWED_VIDEO_EXTENSIONS` | `["mp4","mov","mkv"]` | Accepted containers |
| `CORS_ORIGINS` | localhost / 127.0.0.1:3000 | Browser origins |
| `FFMPEG_BIN` / `FFPROBE_BIN` | `ffmpeg` / `ffprobe` | Executable names or absolute paths |
| `FFPROBE_TIMEOUT_SECONDS` | `60` | Probe timeout |
| `WORKER_AUTOSTART` | `true` | Start worker with the API |
| `WORKER_POLL_INTERVAL_SECONDS` | `1.0` | Queue polling interval |
| `WHISPER_MODEL` | `small` | faster-whisper model name (`tiny`, `base`, `small`, …) |
| `WHISPER_DEVICE` | `cpu` | Inference device |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization; CPU-friendly default |
| `WHISPER_CPU_THREADS` | `4` | CPU inference threads |
| `WHISPER_MODEL_DIR` | `./data/models` | Local model cache (gitignored) |
| `WHISPER_LANGUAGE` | empty | Force a language, or empty to auto-detect |
| `WHISPER_BEAM_SIZE` | `5` | Decoding beam width |
| `WHISPER_VAD_FILTER` | `true` | Drop non-speech audio before decoding |
| `AUDIO_EXTRACT_TIMEOUT_SECONDS` | `3600` | FFmpeg audio-extraction timeout |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Chat model used for clip selection |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Per-request timeout |
| `OLLAMA_TEMPERATURE` | `0.2` | Sampling temperature |
| `OLLAMA_NUM_CTX` | `8192` | Model context window |
| `OLLAMA_KEEP_ALIVE` | `5m` | How long Ollama keeps the model loaded |
| `OLLAMA_THINK` | `false` | Disable reasoning output for structured JSON |
| `MIN_CLIP_SECONDS` / `MAX_CLIP_SECONDS` | `20` / `60` | Preferred target range |
| `CLIP_HARD_MIN_SECONDS` / `CLIP_HARD_MAX_SECONDS` | `15` / `90` | Wider hard limits; must wrap the target range |
| `MAX_CLIPS` | `8` | Maximum stored candidates |
| `CLIP_WINDOW_SECONDS` | `180` | Transcript context window (2–4 min) |
| `CLIP_WINDOW_OVERLAP_SECONDS` | `30` | Overlap between windows; must be below the window |
| `CLIP_MAX_CANDIDATES_PER_CHUNK` | `4` | Per-window proposal cap |
| `CLIP_SCORE_WEIGHTS` | `{"hook":0.25,"clarity":0.25,"payoff":0.20,"emotion_or_interest":0.20,"conciseness":0.10}` | Score weights; normalized to sum to 1 |

Output dimensions and face-sampling settings for later phases are defined and validated but unused. Output dimensions must be an even portrait 9:16 ratio; clip minimum must be below maximum.

The selection prompt itself is editable at `backend/app/prompts/clip_selection.txt`. It is re-read on every job, so prompt changes take effect without restarting the backend. Duration limits, clip count, and score weights are configuration, not prompt text.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Dependency status and upload limits |
| `POST` | `/api/jobs` | Multipart upload (`file`), validates and queues |
| `GET` | `/api/jobs/{id}` | Job state, progress, media metadata, transcript summary |
| `GET` | `/api/jobs/{id}/transcript` | Timestamped transcript JSON (internal pipeline data) |
| `GET` | `/api/jobs/{id}/clips` | Stored candidate clips for a job |
| `GET` | `/api/clips/{id}` | One clip's metadata and heuristic score |
| `GET` | `/api/clips/{id}/file` | Rendered clip file; `404 clip_not_rendered` until Phase 5 |

Errors use a consistent shape:

```json
{ "detail": { "code": "unsupported_file_type", "message": "Unsupported file type. Upload one of: .mp4, .mov, .mkv." } }
```

Status codes: `400 empty_file`, `404 job_not_found`, `404 transcript_not_found`, `404 clip_not_found`, `404 clip_not_rendered`, `413 file_too_large`, `415 unsupported_file_type`, `422` (`unreadable_media`, `no_video_stream`, `unsupported_video_codec`, `invalid_dimensions`, `duration_unknown`), `503 media_tools_unavailable`.

### Job states and progress

`queued → inspecting → transcribing → selecting_clips → completed | failed`

Progress is monotonic: `5` on inspection, `15` when audio preparation starts, `20–80` during transcription, `82` while the transcript is saved, `84–97` during clip selection, and `100` on completion. A job with silent audio or no audio stream still completes with an empty transcript and `has_speech=false`; selection is skipped. The remaining states (`tracking_speakers`, `rendering`, `cancelled`) exist in the enum so later phases and clients do not need a schema change.

Clip selection failures are explicit: if Ollama is unreachable or the configured model is missing, the job fails with a message naming the fix. If the model returns malformed output for one window, that window is skipped and the rest continue. If every window is malformed or no proposal fits the limits, the job completes with zero clips and a clear stage message rather than crashing the worker.

### Transcript format

`GET /api/jobs/{id}/transcript` returns:

```json
{
  "language": "en",
  "language_probability": 0.99,
  "duration": 12.16,
  "model": "small",
  "has_speech": true,
  "created_at": "2026-01-01T00:00:00Z",
  "segments": [
    {
      "start": 0.0,
      "end": 2.28,
      "text": "This is a test recording.",
      "words": [{ "start": 0.0, "end": 0.32, "text": "This" }]
    }
  ]
}
```

Timestamps are absolute seconds relative to the source video, never re-based to a clip. Invalid or non-finite ranges are dropped, timestamps are clamped to the source duration, and non-speech markers such as `[Music]` are filtered out.

### Clip selection

The full transcript is never sent to the LLM in one prompt. Segments are grouped into overlapping windows (`CLIP_WINDOW_SECONDS`, `CLIP_WINDOW_OVERLAP_SECONDS`), and each window keeps absolute source timestamps. For every window, the editable prompt is rendered and sent to Ollama with a JSON schema, `stream: false`, and `think: false` (structured output).

The model only proposes moments and rough 0–10 component ratings. Application code then:

1. Clamps timestamps to the source and the window and rejects `end <= start`.
2. Snaps boundaries to word timestamps, then expands to whole transcript segments so a clip never starts or ends mid-sentence.
3. Fits the range inside `CLIP_HARD_MIN_SECONDS`–`CLIP_HARD_MAX_SECONDS`, trimming or extending whole segments; proposals that cannot fit are rejected.
4. Computes a deterministic weighted **clip potential** score from hook, clarity/standalone, payoff, interest/emotion, and conciseness. Conciseness rewards the target range and gently penalizes the hard edges.
5. Merges proposals whose intersection-over-union is at least 0.55, keeping the higher score.
6. Sorts by source time and keeps at most `MAX_CLIPS`.

The score is a heuristic ranking aid. It is **not** a virality prediction and should not be presented as one.

Before selection the cached Whisper model is released, so Whisper and the LLM are not resident at the same time on a memory-constrained machine.

## Storage

```
backend/data/
├── clipforge.db                 # SQLite (WAL mode)
├── models/                      # faster-whisper model cache (gitignored)
├── uploads/<job-uuid>/source.mp4
├── work/<job-uuid>/transcript.json
└── clips/<job-uuid>/            # reserved for rendered output (Phase 5)
```

Clip proposals are stored as rows in `clips` with start/end/duration, title, hook, reason, score, component scores, and `pending` speaker-tracking/render status. No clip video files are produced yet, so `/api/clips/{id}/file` returns `404 clip_not_rendered`.

During transcription, FFmpeg writes `work/<job-uuid>/audio.wav` (16 kHz mono PCM). It is deleted after transcription; only `transcript.json` remains. Paths are derived from the job UUID only. The original filename is stored as display metadata and sanitized; it is never used to build a filesystem path. Stored relative paths are checked against `DATA_DIR` before use.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes: config path/ratio/extension validation, clip weight/range/Ollama validation, filename sanitization and traversal protection, streamed write limits, ffprobe parsing and failure codes, health responses, upload rejection paths, job persistence across app restarts, empty clip lists, worker queue claims, monotonic progress, interrupted-job recovery, transcript range clamping, non-speech filtering, atomic transcript round-trips, audio extraction, the no-speech and no-audio-stream paths, transcription failure handling, transcript endpoint responses, overlapping transcript windows with absolute timestamps, prompt rendering and placeholder errors, JSON-schema shape, whole-segment boundary snapping, too-short/out-of-bounds/reversed rejection, deterministic weighted scoring, IoU deduplication and count limits, malformed model output handling, Ollama unavailable/missing-model/timeout errors, and clip metadata/file endpoints. Unit tests inject a stub transcriber and stub selector or fake Ollama client, so they never download weights or call a real model.

Frontend verification:

```powershell
cd frontend
npm.cmd run build
```

### Live checks performed

- `POST /api/jobs` with a 12.16 s 640×360 H.264/AAC speech sample → `202`; job reached `completed` / `100`
- `WHISPER_MODEL=tiny` on CPU/INT8 detected `en` with probability 0.999 and produced 3 segments / 20 words with absolute word timestamps
- `GET /api/jobs/{id}/transcript` returned the same data stored in `work/<uuid>/transcript.json`
- `audio.wav` was removed after transcription; no subtitle/caption files were produced
- Peak observed backend working set during tiny-model transcription: about 232 MB
- Silent 5 s video → `completed` with `has_speech=false`, empty segments, and a clear stage message
- Video with no audio stream → `completed` with `has_speech=false`, `audio_codec=null`, empty segments
- Phase 3: 92.75 s speech video → health reported Ollama `0.40.15` with the configured model; progress advanced through transcription, `selecting_clips` (`84`), and `completed` (`100`)
- Phase 3: the installed `huihui_ai/deepseek-r1-abliterated:1.5b` model (set via `OLLAMA_MODEL`) produced a stored 20.5 s candidate with score `91.0`, component scores, hook, and reason
- Phase 3: nested/overlapping model proposals were collapsed by deduplication; the final job stored one candidate instead of four near-duplicates
- Phase 3: `GET /api/jobs/{id}/clips` and `GET /api/clips/{id}` returned the stored proposal with `render_status=pending` and `speaker_tracking_status=pending`; `GET /api/clips/{id}/file` returned `404 clip_not_rendered`
- Phase 3: a run with the default 180 s request timeout failed with the actionable `Ollama did not respond within 180 seconds…` message instead of hanging or crashing the worker
- Phase 3: the editable prompt was re-read without a restart, and prompt calibration plus containment dedup changed the next run's output as intended
- Corrupt `.mp4` → `422 unreadable_media`; `.txt` → `415 unsupported_file_type`; unknown job UUID → `404 job_not_found`; unknown clip UUID → `404 clip_not_found`

## Current limitations

- No speaker tracking, captions, music, branding, or 9:16 rendering yet; clips are proposals only
- CPU-only transcription by default; long videos are slow, and `small` is much slower than `tiny`
- Clip selection quality depends on the installed local model; small models can miss moments or return malformed JSON (those windows are skipped)
- The default `qwen2.5:3b` model must be pulled before selection works; the health check reports it as unavailable until then
- The first transcription of a model requires internet access and enough disk space
- One job is processed at a time; the UI uploads one file at a time
- No job cancellation/deletion endpoint (planned for a later phase)
- Upload is validated synchronously; very large files hold the request open until probing finishes
- Uploaded originals are never cleaned up automatically
- Transcripts are stored and exposed as JSON, but the UI only shows a summary, not the full text
- Selection is sequential per window, so very long recordings can take a while on CPU-only hardware
