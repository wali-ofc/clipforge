# ClipForge

Local-first AI video clipping. Long recordings go in; short vertical clips come out — processed entirely on your machine, with no cloud services and no accounts.

> **Build status: Phase 0 + Phase 1 complete.**
> Uploads are streamed to disk, validated with `ffprobe`, persisted in SQLite, and processed by a single background worker. Transcription, AI moment selection, speaker tracking, captions, and 9:16 rendering are **not implemented yet**.

## What works today

- Typed configuration from `.env` files and environment variables
- Health endpoint reporting database, `ffmpeg`, and `ffprobe` availability
- Streamed, chunked uploads written straight to disk (never buffered fully in memory)
- Immediate `ffprobe` validation: extension, size, readability, video stream, duration, codec
- Persistent jobs in SQLite with monotonic progress and stage messages
- Single worker that claims the oldest queued job and recovers interrupted jobs on startup
- Minimal Next.js UI: drag/drop upload, upload progress, live job status polling, error states
- Metadata exposed over the API; clip list endpoint returns `[]` for now

## Repository layout

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── api/          # health, upload, job routes + error/dep helpers
│   │   ├── models/       # SQLAlchemy Job and Clip models
│   │   ├── schemas/      # Pydantic response models
│   │   ├── services/     # ffprobe probing, tool availability
│   │   ├── utils/        # config-independent helpers (files, paths, subprocess)
│   │   ├── worker/       # queue runner and Phase 1 pipeline
│   │   ├── config.py     # typed settings
│   │   ├── db.py         # engine, sessions, schema creation
│   │   └── main.py       # FastAPI app + lifespan
│   ├── tests/            # 42 pytest tests
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

Later-phase settings (`OLLAMA_*`, `WHISPER_*`, clip length limits, output dimensions, face sampling) are already defined and validated but unused. Output dimensions must be an even portrait 9:16 ratio; clip minimum must be below maximum.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Dependency status and upload limits |
| `POST` | `/api/jobs` | Multipart upload (`file`), validates and queues |
| `GET` | `/api/jobs/{id}` | Job state, progress, media metadata |
| `GET` | `/api/jobs/{id}/clips` | Clips for a job; `[]` in Phase 1 |

Errors use a consistent shape:

```json
{ "detail": { "code": "unsupported_file_type", "message": "Unsupported file type. Upload one of: .mp4, .mov, .mkv." } }
```

Status codes: `400 empty_file`, `404 job_not_found`, `413 file_too_large`, `415 unsupported_file_type`, `422` (`unreadable_media`, `no_video_stream`, `unsupported_video_codec`, `invalid_dimensions`, `duration_unknown`), `503 media_tools_unavailable`.

### Job states

`queued → inspecting → completed | failed`

The remaining states (`transcribing`, `selecting_clips`, `tracking_speakers`, `rendering`, `cancelled`) exist in the enum so later phases and clients do not need a schema change. Phase 1 stops at `completed` with progress `100` and the message “Source validated. Automatic clip generation is not enabled in this build phase.”

## Storage

```
backend/data/
├── clipforge.db                 # SQLite (WAL mode)
├── uploads/<job-uuid>/source.mp4
├── work/<job-uuid>/             # reserved for later phases
└── clips/<job-uuid>/            # reserved for later phases
```

Paths are derived from the job UUID only. The original filename is stored as display metadata and sanitized; it is never used to build a filesystem path. Stored relative paths are checked against `DATA_DIR` before use.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes: config path/ratio/extension validation, filename sanitization and traversal protection, streamed write limits, ffprobe parsing and failure codes, health responses, upload rejection paths, job persistence across app restarts, empty clip lists, worker queue claims, monotonic progress, and interrupted-job recovery.

Frontend verification:

```powershell
cd frontend
npm.cmd run build
```

### Live checks performed

- `POST /api/jobs` with a 4 s 640×360 H.264/AAC sample → `202`, job queued, worker reached `completed` / `100`
- `GET /api/jobs/{id}/clips` → `[]`
- Corrupt `.mp4` → `422 unreadable_media`; `.txt` → `415 unsupported_file_type`; unknown UUID → `404 job_not_found`
- Files stored at `uploads/<uuid>/source.mp4`; SQLite row confirms UUID id, relative `stored_path`, and metadata

## Current limitations

- No transcription, moment selection, speaker tracking, captions, music, branding, or rendering
- No job cancellation/deletion endpoint (planned for a later phase)
- Upload is validated synchronously; very large files hold the request open until probing finishes
- Single-process worker only, by design for local use
- One upload at a time in the UI; no resume/chunked retry of interrupted uploads
- Uploaded originals are never cleaned up automatically
