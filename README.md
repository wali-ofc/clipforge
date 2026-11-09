# ClipForge

Local-first AI video clipping. Long recordings go in; short vertical clips come out — processed entirely on your machine, with no cloud services and no accounts.

> **Build status: Phase 0 + Phase 1 + Phase 2 complete.**
> Uploads are streamed to disk, validated with `ffprobe`, persisted in SQLite, and processed by a single background worker. The worker now extracts audio with FFmpeg and transcribes it locally with faster-whisper, storing a timestamped transcript. AI moment selection, speaker tracking, captions, and 9:16 rendering are **not implemented yet**.

## What works today

- Typed configuration from `.env` files and environment variables
- Health endpoint reporting database, `ffmpeg`, `ffprobe`, and faster-whisper availability
- Streamed, chunked uploads written straight to disk (never buffered fully in memory)
- Immediate `ffprobe` validation: extension, size, readability, video stream, duration, codec
- Persistent jobs in SQLite with monotonic progress and stage messages
- Single worker that claims the oldest queued job and recovers interrupted jobs on startup
- Local CPU/INT8 transcription with faster-whisper, including word-level timestamps
- Graceful handling of silent audio and videos with no audio stream (empty transcript, job still completes)
- Minimal Next.js UI: drag/drop upload, upload progress, live job status polling, transcript summary, error states
- Metadata and transcript exposed over the API; clip list endpoint returns `[]` for now

Captions are intentionally **not** generated or burned into any video. The transcript is internal pipeline data for later phases.

## Repository layout

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── api/          # health, upload, job/transcript routes + error/dep helpers
│   │   ├── models/       # SQLAlchemy Job and Clip models
│   │   ├── schemas/      # Pydantic response and transcript models
│   │   ├── services/     # ffprobe probing, tool checks, transcription
│   │   ├── utils/        # config-independent helpers (files, paths, subprocess)
│   │   ├── worker/       # queue runner and inspection/transcription pipeline
│   │   ├── config.py     # typed settings
│   │   ├── db.py         # engine, sessions, schema creation + additive migrations
│   │   └── main.py       # FastAPI app + lifespan
│   ├── tests/            # 68 pytest tests
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
| Ollama | not used yet | Only needed from Phase 3 onward |
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

Later-phase settings (`OLLAMA_*`, clip length limits, output dimensions, face sampling) are already defined and validated but unused. Output dimensions must be an even portrait 9:16 ratio; clip minimum must be below maximum.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Dependency status and upload limits |
| `POST` | `/api/jobs` | Multipart upload (`file`), validates and queues |
| `GET` | `/api/jobs/{id}` | Job state, progress, media metadata, transcript summary |
| `GET` | `/api/jobs/{id}/transcript` | Timestamped transcript JSON (internal pipeline data) |
| `GET` | `/api/jobs/{id}/clips` | Clips for a job; `[]` in Phase 2 |

Errors use a consistent shape:

```json
{ "detail": { "code": "unsupported_file_type", "message": "Unsupported file type. Upload one of: .mp4, .mov, .mkv." } }
```

Status codes: `400 empty_file`, `404 job_not_found`, `404 transcript_not_found`, `413 file_too_large`, `415 unsupported_file_type`, `422` (`unreadable_media`, `no_video_stream`, `unsupported_video_codec`, `invalid_dimensions`, `duration_unknown`), `503 media_tools_unavailable`.

### Job states and progress

`queued → inspecting → transcribing → completed | failed`

Progress is monotonic: `5` on inspection, `15` when audio preparation starts, `20–95` during transcription, `98` while the transcript is saved, and `100` on completion. A job with silent audio or no audio stream still completes with an empty transcript and `has_speech=false`. The remaining states (`selecting_clips`, `tracking_speakers`, `rendering`, `cancelled`) exist in the enum so later phases and clients do not need a schema change.

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

## Storage

```
backend/data/
├── clipforge.db                 # SQLite (WAL mode)
├── models/                      # faster-whisper model cache (gitignored)
├── uploads/<job-uuid>/source.mp4
├── work/<job-uuid>/transcript.json
└── clips/<job-uuid>/            # reserved for later phases
```

During transcription, FFmpeg writes `work/<job-uuid>/audio.wav` (16 kHz mono PCM). It is deleted after transcription; only `transcript.json` remains. Paths are derived from the job UUID only. The original filename is stored as display metadata and sanitized; it is never used to build a filesystem path. Stored relative paths are checked against `DATA_DIR` before use.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes: config path/ratio/extension validation, filename sanitization and traversal protection, streamed write limits, ffprobe parsing and failure codes, health responses, upload rejection paths, job persistence across app restarts, empty clip lists, worker queue claims, monotonic progress, interrupted-job recovery, transcript range clamping, non-speech filtering, atomic transcript round-trips, audio extraction, the no-speech and no-audio-stream paths, transcription failure handling, and transcript endpoint responses. Unit tests inject a stub transcriber or fake Whisper model, so they never download weights.

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
- `GET /api/jobs/{id}/clips` → `[]`; corrupt `.mp4` → `422 unreadable_media`; `.txt` → `415 unsupported_file_type`; unknown UUID → `404 job_not_found`

## Current limitations

- No moment selection, speaker tracking, captions, music, branding, or 9:16 rendering yet
- CPU-only transcription by default; long videos are slow, and `small` is much slower than `tiny`
- The first transcription of a model requires internet access and enough disk space
- One job is processed at a time; the UI uploads one file at a time
- No job cancellation/deletion endpoint (planned for a later phase)
- Upload is validated synchronously; very large files hold the request open until probing finishes
- Uploaded originals are never cleaned up automatically
- Transcripts are stored and exposed as JSON, but the UI only shows a summary, not the full text
