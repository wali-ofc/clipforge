# ClipForge

Local-first AI video clipping. Long recordings go in; short vertical clips come out — processed entirely on your machine, with no cloud services and no accounts.

> **Build status: Phase 0 + Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 complete.**
> Uploads are streamed to disk, validated with `ffprobe`, persisted in SQLite, and processed by a single background worker. The worker extracts audio with FFmpeg, transcribes it locally with faster-whisper, asks a local Ollama model for self-contained candidate moments, samples frames only inside each selected candidate to build face tracks and a smoothed 9:16 crop plan, then renders every selected clip as a verified H.264/AAC MP4 with a time-varying portrait crop. Captions and music are still **not implemented**, by design.

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
- Face sampling only inside each candidate range, with a modular detector interface (OpenCV YuNet by default)
- Face-track association across samples, heuristic active-speaker estimation, and a stable largest/central-face fallback
- Time-indexed crop plans in source-frame pixels with EMA smoothing, a dead zone, a crop-speed limit, and interpolation for rendering
- Explicit tracking status and confidence on every clip; detection failure holds the last stable crop briefly and then centres
- Per-clip FFmpeg rendering with a time-varying 9:16 crop driven by the stored plan, H.264 video, AAC audio, and `+faststart`
- Every rendered file is probed with ffprobe for dimensions, codecs, container, audio presence, frame rate, and duration before it is marked complete
- Configurable output resolution (`1080×1920` default, `720×1280` supported), frame rate, CRF, preset, and render timeout
- Minimal Next.js UI: drag/drop upload, upload progress, live job status polling, transcript summary, clip cards with tracking and render status, error states
- Metadata, transcript, clip proposals, crop plans, and rendered MP4 files exposed over the API

Captions are intentionally **not** generated or burned into any video. The transcript is internal pipeline data. No music, text, or watermark is added during rendering.

## Repository layout

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── api/          # health, upload, job/transcript, clip routes + helpers
│   │   ├── models/       # SQLAlchemy Job and Clip models
│   │   ├── prompts/      # editable clip-selection prompt
│   │   ├── schemas/      # Pydantic response, transcript, and LLM models
│   │   ├── services/     # probing, tool checks, transcription, Ollama, selection, tracking, rendering
│   │   ├── utils/        # config-independent helpers (files, paths, subprocess)
│   │   ├── worker/       # queue runner and inspection/transcription/selection/tracking/render pipeline
│   │   ├── config.py     # typed settings
│   │   ├── db.py         # engine, sessions, schema creation + additive migrations
│   │   └── main.py       # FastAPI app + lifespan
│   ├── tests/            # 138 pytest tests
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
| OpenCV | 4.14 (`opencv-python-headless`) | Installed with backend dependencies; used by the face detector |
| YuNet model | downloaded once | `backend/data/models/face_detection_yunet_2023mar.onnx` (~230 KB) |

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

Speaker tracking also needs the YuNet face model. It is not bundled with the repository, so download it once into the model directory:

```powershell
New-Item -ItemType Directory -Force backend/data/models | Out-Null
Invoke-WebRequest `
  -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" `
  -OutFile backend/data/models/face_detection_yunet_2023mar.onnx
```

If the model or OpenCV is missing, the app still starts and jobs still complete. Each clip is marked `unavailable` and receives a centred crop plan; the health endpoint reports `face_detection` as unavailable with the exact fix.

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
| `FACE_SAMPLE_FPS` | `2` | Frame sampling rate inside each candidate clip (max 15) |
| `FACE_DETECTOR_MODEL_PATH` | `./data/models/face_detection_yunet_2023mar.onnx` | YuNet ONNX model file |
| `FACE_DETECTOR_SCORE_THRESHOLD` | `0.6` | Minimum face confidence |
| `FACE_DETECTOR_NMS_THRESHOLD` | `0.3` | Non-maximum-suppression threshold |
| `FACE_DETECTOR_TOP_K` | `5000` | Detector candidate cap |
| `FACE_DETECTOR_MIN_SIZE` | `32` | Minimum face box size in pixels |
| `FACE_TRACK_IOU_THRESHOLD` | `0.2` | IoU needed to associate a face across samples |
| `FACE_TRACK_MAX_GAP_SECONDS` | `1.0` | Maximum gap before a track is closed |
| `FACE_TRACK_MIN_OBSERVATIONS` | `2` | Observations needed for a track |
| `SPEAKER_CONFIDENCE_THRESHOLD` | `0.55` | Below this the stable fallback face is used |
| `SPEAKER_SWITCH_MARGIN` | `0.12` | Margin a different face needs to replace the fallback |
| `CROP_EMA_ALPHA` | `0.35` | EMA weight for new crop positions |
| `CROP_DEAD_ZONE_RATIO` | `0.015` | Dead zone as a fraction of crop width |
| `CROP_MAX_SPEED_RATIO` | `0.5` | Maximum crop movement in crop widths per second |
| `CROP_HOLD_SECONDS` | `2.0` | Hold the last stable crop after detection disappears |
| `OUTPUT_WIDTH` / `OUTPUT_HEIGHT` | `1080` / `1920` | Portrait output resolution; must be even and 9:16 (`720×1280` also valid) |
| `OUTPUT_FPS` | `30` | Constant output frame rate; broad player compatibility |
| `OUTPUT_CRF` | `23` | H.264 quality (lower is larger/better, `0–51`) |
| `OUTPUT_PRESET` | `veryfast` | x264 speed/size preset |
| `RENDER_TIMEOUT_SECONDS` | `600` | Per-clip FFmpeg render timeout |

Output dimensions must be an even portrait 9:16 ratio; the crop planner derives its target aspect from them. `720×1280` is supported for faster or smaller renders. Clip minimum must be below maximum.

The selection prompt itself is editable at `backend/app/prompts/clip_selection.txt`. It is re-read on every job, so prompt changes take effect without restarting the backend. Duration limits, clip count, and score weights are configuration, not prompt text.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Dependency status and upload limits |
| `POST` | `/api/jobs` | Multipart upload (`file`), validates and queues |
| `GET` | `/api/jobs/{id}` | Job state, progress, media metadata, transcript summary |
| `GET` | `/api/jobs/{id}/transcript` | Timestamped transcript JSON (internal pipeline data) |
| `GET` | `/api/jobs/{id}/clips` | Stored candidate clips for a job |
| `GET` | `/api/clips/{id}` | One clip's metadata, heuristic score, tracking status, and crop plan |
| `GET` | `/api/clips/{id}/file` | Rendered portrait MP4; `404 clip_not_rendered` until rendering succeeds |

Errors use a consistent shape:

```json
{ "detail": { "code": "unsupported_file_type", "message": "Unsupported file type. Upload one of: .mp4, .mov, .mkv." } }
```

Status codes: `400 empty_file`, `404 job_not_found`, `404 transcript_not_found`, `404 clip_not_found`, `404 clip_not_rendered`, `413 file_too_large`, `415 unsupported_file_type`, `422` (`unreadable_media`, `no_video_stream`, `unsupported_video_codec`, `invalid_dimensions`, `duration_unknown`), `503 media_tools_unavailable`.

### Job states and progress

`queued → inspecting → transcribing → selecting_clips → tracking_speakers → rendering → completed | failed`

Progress is monotonic: `5` on inspection, `15` when audio preparation starts, `20–80` during transcription, `82` while the transcript is saved, `84–97` during clip selection, `97–98` during speaker tracking and crop planning, `98–99` while clips render, and `100` on completion. A job with silent audio or no audio stream still completes with an empty transcript and `has_speech=false`; selection, tracking, and rendering are skipped. `cancelled` exists in the enum so later phases and clients do not need a schema change.

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

### Speaker tracking and crop plans

Speaker tracking runs only after clip selection and only inside each candidate range. FFmpeg seeks to the candidate start, decodes at most that range, and writes frames at `FACE_SAMPLE_FPS`; the whole source is never scanned. Frames are deleted when the clip finishes.

1. **Detection.** The modular `FaceDetector` protocol is implemented by `OpenCVYuNetDetector` (OpenCV YuNet ONNX). A different detector can be supplied without changing the tracker. Detections are in decoded, display-oriented frame pixels, so rotation metadata is already applied.
2. **Tracks.** Boxes are associated across samples by IoU, with a centre-distance fallback for small movements and short gaps (`FACE_TRACK_*`). Each track keeps its observations and a cheap lower-face motion signal.
3. **Active speaker.** With one visible face, that face is used. With several, each candidate is scored from face size, centrality, continuity with the previous choice, transcript speech timing, mouth-region motion, and detector confidence. If the resulting confidence is below `SPEAKER_CONFIDENCE_THRESHOLD`, the planner keeps a stable largest/central face (with `SPEAKER_SWITCH_MARGIN` hysteresis) instead of switching rapidly.
4. **Crop geometry.** The planner works in source pixels. For a wide source it uses the full height, so a 9:16 crop is `source_height * 9 / 16` wide; a source already narrower than the target uses full width and crops height. The crop is always clamped inside the source. A source already at 9:16 is not cropped unnecessarily.
5. **Smoothing.** Crop centres are smoothed with an EMA (`CROP_EMA_ALPHA`), a dead zone (`CROP_DEAD_ZONE_RATIO` of crop width), and a speed limit (`CROP_MAX_SPEED_RATIO` crop widths per second). Samples are stored at clip-relative timestamps; rendering interpolates between them with `interpolate_crop()`.
6. **Fallback.** If a face disappears, the last stable crop is held for `CROP_HOLD_SECONDS`, then the plan moves to a centred crop. If detection cannot run at all, every clip still receives an explicit centred plan and status; the job is never failed by tracking.

Tracking is persisted per clip as `speaker_tracking_status`, `speaker_tracking_confidence`, `crop_plan`, and `tracking_details`. Statuses are `tracked`, `single_face`, `fallback`, `no_faces`, `no_frames`, `unavailable`, `failed`, and `pending`. A centred crop is always labelled as such; it is never presented as successful tracking.

The active-speaker estimate is a heuristic. **No lip-sync or speaker-diarization model is used.** Confidence and fallback behaviour are exposed so the UI can be honest about uncertainty.

`crop_plan` shape (coordinates are source pixels, times are clip-relative seconds):

```json
{
  "version": 1,
  "coordinate_space": "source_pixels",
  "time_space": "clip_relative_seconds",
  "method": "ema+dead-zone+speed-limit",
  "target_aspect": 0.5625,
  "source": { "width": 1920, "height": 1080 },
  "crop": { "width": 607.5, "height": 1080 },
  "samples": [
    {
      "time": 0.0,
      "x": 760.0,
      "y": 540.0,
      "crop_width": 607.5,
      "crop_height": 1080.0,
      "confidence": 0.91,
      "status": "tracked",
      "face_count": 1
    }
  ]
}
```

`tracking_details` records the method, detector, sampling rate, sampled/face frame counts, track and speech-interval counts, fallback behaviour, limitations, and a status reason or error code when applicable.

### Clip rendering

Rendering runs after tracking, for every stored candidate. Each clip is cut from the original source at its stored `start_seconds`/`end_seconds`, reframed to 9:16, and encoded as its own MP4 under `backend/data/clips/{job_id}/{clip_id}.mp4`. The source is streamed by FFmpeg; it is never decoded into application memory.

1. **Dynamic crop.** The stored crop plan is interpolated at clip-relative time. FFmpeg's `crop` filter receives `x`/`y` updates through a generated `sendcmd` command file at 25 Hz (`CROP_COMMAND_STEP_SECONDS`). Crop width/height are fixed per clip from the same target-aspect geometry used by the tracker, rounded to even values for 4:2:0.
2. **Scale and encode.** The cropped frame is scaled to `OUTPUT_WIDTH`×`OUTPUT_HEIGHT` with bicubic filtering, given square pixels (`setsar=1`), and converted to `yuv420p`. Video is H.264 (`libx264`) with configurable `OUTPUT_CRF` and `OUTPUT_PRESET`; audio is AAC at 192 kbit/s. `+faststart` moves the MP4 index to the front for streaming.
3. **Frame rate.** Output is constant `OUTPUT_FPS` (default 30) for broad player compatibility, regardless of the source's frame rate.
4. **Stream mapping.** Only the first video stream and, when the source has audio, the first audio stream are mapped. Subtitles and data streams are explicitly excluded (`-sn`, `-dn`). No text, watermark, music, or caption filter is ever added.
5. **Verification.** Every output is probed with ffprobe before the clip is marked `completed`. Dimensions must equal the configured resolution, video must be H.264, container must be MP4, audio must be present and AAC when the source had audio, frame rate must match `OUTPUT_FPS`, and duration must be within `max(0.6 s, 4%)` of the clip duration. A failed check deletes the partial file and records a per-clip error.

**Tradeoffs.** A per-frame crop expression would be enormous for long clips and risks Windows command-line limits. The `sendcmd` approach keeps the command line short and memory flat, at the cost of updating the crop position every 40 ms rather than on every output frame. Because the command interval is finer than a 30 fps frame and the plan is already smoothed, the difference is not visible. The command file is temporary and lives under `work/{job_id}/render`; it is deleted after each clip, and the render/tracking directories are removed when the job finishes.

A single clip failure does not fail the job. The clip is marked `failed` with its error, its `output_filename` is cleared, and the remaining clips continue. If every clip fails, the job still completes with an explicit stage message; `/api/clips/{id}/file` returns `404 clip_not_rendered` for failed clips.

## Storage

```
backend/data/
├── clipforge.db                 # SQLite (WAL mode)
├── models/                      # faster-whisper cache + YuNet ONNX model (gitignored)
├── uploads/<job-uuid>/source.mp4
├── work/<job-uuid>/transcript.json
├── work/<job-uuid>/tracking/<clip-uuid>/   # temporary sampled frames, deleted after tracking
├── work/<job-uuid>/render/                 # temporary crop command files, deleted after rendering
└── clips/<job-uuid>/<clip-uuid>.mp4        # verified portrait output
```

Clip rows store start/end/duration, title, hook, reason, score, component scores, speaker-tracking status/confidence, crop plan, tracking details, render status/error, output path, and output dimensions. Rendered files are served by `/api/clips/{id}/file`; a clip is downloadable only after it has been marked `completed`.

During transcription, FFmpeg writes `work/<job-uuid>/audio.wav` (16 kHz mono PCM). It is deleted after transcription; only `transcript.json` remains. Tracking and render temporary directories are removed when the job finishes, and only verified clip MP4s remain under `clips/`. Paths are derived from the job UUID only. The original filename is stored as display metadata and sanitized; it is never used to build a filesystem path. Stored relative paths are checked against `DATA_DIR` before use.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Coverage includes: config path/ratio/extension validation, clip weight/range/Ollama validation, filename sanitization and traversal protection, streamed write limits, ffprobe parsing and failure codes, health responses, upload rejection paths, job persistence across app restarts, legacy SQLite additive migrations, empty clip lists, worker queue claims, monotonic progress, interrupted-job recovery, transcript range clamping, non-speech filtering, atomic transcript round-trips, audio extraction, the no-speech and no-audio-stream paths, transcription failure handling, transcript endpoint responses, overlapping transcript windows with absolute timestamps, prompt rendering and placeholder errors, JSON-schema shape, whole-segment boundary snapping, too-short/out-of-bounds/reversed rejection, deterministic weighted scoring, IoU deduplication and count limits, malformed model output handling, Ollama unavailable/missing-model/timeout errors, crop geometry for wide/portrait/exact-9:16 sources, face-track association, speech-interval merging, single-face and multi-face speaker selection, mouth-motion cueing, stable low-confidence fallback, hold-then-centre behaviour, dead-zone and speed-limit smoothing, crop-plan interpolation, explicit centred fallback, missing-model errors, tracker orchestration with an injected detector, crop command generation and clamping, output verification for dimensions/codecs/audio/duration/frame rate, real FFmpeg renders with and without audio, a rendered dynamic crop that visibly follows the plan, per-clip render failure handling, and clip metadata/file endpoints. Unit tests inject a stub transcriber, stub selector, stub speaker tracker, and stub renderer (or fake Ollama client), so they never download weights, load the face model, call a real model, or render real video unless a test is explicitly marked as an FFmpeg integration test.

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
- Phase 4: health reported `face_detection` available with OpenCV `4.14.0.94`, YuNet, and 2 fps sampling; `ollama` reported `qwen2.5:3b`
- Phase 4: a real `qwen2.5:3b` probe returned reachable, model available, and valid structured JSON
- Phase 4: YuNet detected the face in a 512×512 still at confidence 0.909
- Phase 4: an 8 s 1280×720 single-face sample → `tracked`, 16/16 frames with a face, one track, confidence 0.962; the crop centre followed the moving face within the speed limit
- Phase 4: an 8 s two-face sample with mouth-region motion → `tracked`, two tracks, confidence 0.973; the plan followed the moving/mouth-active face
- Phase 4: an 8 s two-face sample with no motion cue → mixed `fallback`/`tracked` with one stable face and no switching; confidence 0.85
- Phase 4: an 8 s sample with no faces → `no_faces`, confidence 0.0, every crop sample `centered` at the source centre
- Phase 4: sampled frame directories were removed after each clip, and crop plans interpolated correctly at intermediate timestamps
- Phase 4 end-to-end: a 66.7 s 1280×720 talking-head video with real speech ran `upload → inspecting → transcribing → selecting_clips → tracking_speakers → completed`; `qwen2.5:3b` proposed 4 clips and all 4 were stored as `tracked` (confidence `0.953`–`0.957`, `render_status=pending`)
- Phase 4 end-to-end: every stored crop plan used `coordinate_space=source_pixels`, `time_space=clip_relative_seconds`, a `405×720` crop (`720 × 9 / 16`), 41–50 samples, and source dimensions `1280×720`; tracking details recorded 1 track, 100% face frames, and 3–6 speech intervals per clip
- Phase 4 end-to-end: crop movement stayed within the configured speed limit at the 2 fps sampling rate, with no rapid switching
- Phase 4 timeout caveat: with the default `OLLAMA_TIMEOUT_SECONDS=180`, `qwen2.5:3b` on this CPU exceeded the limit during `selecting_clips` and the job failed with the actionable timeout message. Raising the timeout (and `OLLAMA_KEEP_ALIVE`) let the same job finish; the default stays at 180 s so slow machines get a clear error rather than an indefinite hang
- Phase 5: all four clips from the Phase 4 66.7 s 1280×720 job were rendered from their stored crop plans to `1080×1920` H.264/AAC at 30 fps. Durations were `25.10`, `20.68`, `22.38`, and `20.37` s; files were 1.0–1.1 MB at CRF 23 / `veryfast`
- Phase 5: ffprobe confirmed every output was MP4 with exactly one H.264 video stream and one AAC audio stream, no subtitles or data streams, and a duration matching the requested range
- Phase 5: YuNet detected the speaker in rendered frames at relative positions x `0.45–0.53`, y `0.47–0.52`, confirming the time-varying crop kept the face well framed across all four clips
- Phase 5: a synthetic red/blue source rendered with a left-to-right crop plan changed from red to blue over time, proving the dynamic `sendcmd` crop actually moves rather than staying static
- Phase 5: temporary `render` command files were removed after each clip, and a simulated renderer failure marked the clip `failed`, cleared its output path, and returned `404 clip_not_rendered`
- Corrupt `.mp4` → `422 unreadable_media`; `.txt` → `415 unsupported_file_type`; unknown job UUID → `404 job_not_found`; unknown clip UUID → `404 clip_not_found`

## Current limitations

- Captions, music, text, and watermarks are intentionally not added; clips are plain portrait MP4s
- Rendering is CPU-only (`libx264`) and re-encodes every clip; long or high-resolution sources take time
- The dynamic crop updates at 25 Hz rather than per output frame; the plan is already smoothed, so this is not visible in normal footage
- Active-speaker detection is heuristic (size, centrality, continuity, speech timing, mouth motion). It is not lip-sync or diarization, so it can follow the wrong face when speakers overlap, are similarly sized, or are off-centre
- Tracking samples at `FACE_SAMPLE_FPS` (2 fps by default). Very fast movement between samples is smoothed and may lag slightly
- Face detection depends on OpenCV and the YuNet model; without them every clip gets an explicit centred crop
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
