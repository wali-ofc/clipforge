# Running ClipForge

ClipForge turns a long video into short 9:16 clips, entirely on your machine.
It runs as two local processes plus two external tools:

- a FastAPI backend with one background worker (port `8000`)
- a Next.js frontend (port `3000`)
- FFmpeg / ffprobe for media inspection and rendering
- Ollama for local clip selection

No account, API key, or cloud service is required. Uploaded videos, work files,
rendered clips, the SQLite database, and downloaded models all live under
`backend/data/`, which is gitignored.

---

## 1. What you need

| Tool | Version used | Notes |
| --- | --- | --- |
| Python | 3.11.x | Backend requires `>=3.11,<3.12` |
| Node.js | 20+ (26 used) | Frontend dev server and build |
| FFmpeg / ffprobe | 9.0.2 | On `PATH`, or set `FFMPEG_BIN` / `FFPROBE_BIN` |
| Ollama | 0.40+ | Local LLM server; the default model is `qwen2.5:3b` |
| Disk | 10 GB+ free recommended | Models, uploads (up to 5 GiB each), work files, and rendered clips |
| RAM | 16 GB comfortable | Whisper is unloaded before Ollama runs, but the machine still gets busy |

Internet is needed once to install packages, pull the Ollama model, download the
Whisper model on first transcription, and download the YuNet face model.

---

## 2. One-time setup

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

A fully resolved dependency list is in `backend/requirements.lock.txt`.

### Ollama

Install [Ollama](https://ollama.com/), start the server, and pull the default
model:

```powershell
ollama serve
```

In a second terminal:

```powershell
ollama pull qwen2.5:3b
```

`qwen2.5:3b` is the default because it fits on a 16 GB machine. Any installed
chat model can be used by setting `OLLAMA_MODEL`. Verify what is installed and
what is loaded with:

```powershell
ollama list
ollama ps
```

### Whisper model

The first transcription downloads the configured Whisper model into
`backend/data/models`. For a quick smoke test, use `tiny`; the default `small`
is slower on CPU:

```powershell
$env:WHISPER_MODEL = "tiny"
```

Put that in `backend/.env` if you want it to persist.

### YuNet face model

Speaker tracking needs the YuNet ONNX model. Download it once:

```powershell
New-Item -ItemType Directory -Force backend/data/models | Out-Null
Invoke-WebRequest `
  -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" `
  -OutFile backend/data/models/face_detection_yunet_2023mar.onnx
```

If the model or OpenCV is missing, jobs still complete: clips are marked
`unavailable` and use a centred crop instead of speaker tracking. The health
endpoint reports the exact fix.

### Frontend

```powershell
cd frontend
npm.cmd install
Copy-Item .env.local.example .env.local
```

`.env.local` only contains the backend URL:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

## 3. Start it

Use two terminals.

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

Then open:

- UI: <http://localhost:3000> (or <http://127.0.0.1:3000>)
- API: <http://127.0.0.1:8000>
- Interactive API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

Check the backend dependencies before uploading:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 5
```

`checks.ffmpeg`, `checks.ffprobe`, `checks.ollama`, and `checks.face_detection`
should report `available: true`. Ollama problems include an actionable `detail`
string.

The worker starts automatically with the API (`WORKER_AUTOSTART=true`). Jobs left
in an active state by a crash are marked `failed` on the next startup, and
orphan UUID directories with no database row are removed.

> Keep the two dev servers on the same hostname you open in the browser. If HMR
> behaves oddly, use `http://localhost:3000` consistently rather than switching
> between `localhost` and `127.0.0.1`.

---

## 4. Run a job

1. Drag an `.mp4`, `.mov`, or `.mkv` file onto the upload panel.
2. The backend streams it to `uploads/<job-uuid>/source.mp4`, validates it with
   ffprobe, and queues it.
3. The job page polls and shows each stage: inspecting, extracting audio,
   transcribing, selecting clips, tracking, rendering.
4. When it completes, preview each clip in the browser or download the MP4.
5. Use **Cancel & delete job** while queued/processing, or **Delete job & media**
   once terminal, to remove the job row and all of its files.

Only one job runs at a time. Uploading another file while a job is active is
allowed, but it waits in the queue.

### Where files go

```text
backend/data/
├── clipforge.db                  # jobs and clip metadata
├── models/                       # Whisper + YuNet models (download once)
├── uploads/<job-uuid>/source.mp4 # original upload
├── work/<job-uuid>/              # transcript, temporary tracking/render files
└── clips/<job-uuid>/<clip-uuid>.mp4
```

The database stores display metadata only. Paths are derived from UUIDs, and the
original filename is never used to build a path.

---

## 5. Stopping and resetting

- Stop each terminal with `Ctrl+C`.
- Delete individual jobs from the UI; this removes the database rows and the
  `uploads/`, `work/`, and `clips/` directories for that job.
- To reset everything, stop the backend first, then delete `backend/data/`.
  The database and directories are recreated on the next start. Models are
  re-downloaded unless you keep `backend/data/models/`.
- `backend/data/` is gitignored, so uploads and renders are never committed.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Health shows Ollama unavailable | Ollama is not running | `ollama serve`, then reload `/api/health` |
| `ollama_model_missing` | Configured model is not installed | `ollama pull <model>` or change `OLLAMA_MODEL` |
| Job fails at 84% with `ollama_timeout` | Ollama did not finish within `OLLAMA_TIMEOUT_SECONDS` | See [section 7](#7-why-ollama-sometimes-does-not-respond-within-180-seconds) |
| Job stays near 22% while loading the Whisper model | The first run is downloading the configured model; it needs internet access and several hundred MB of free disk space | Check that `huggingface.co` is reachable. The Windows symlink warning is harmless. For a smaller download, set `WHISPER_MODEL=tiny` in `backend/.env`, restart the backend, and upload again |
| `507 insufficient_disk_space` | Data drive is below `MIN_FREE_DISK_BYTES` (1 GiB) | Free space or lower the guard |
| `413 file_too_large` | Upload exceeds `MAX_UPLOAD_BYTES` (5 GiB) | Use a smaller file or raise the limit |
| `422 unreadable_media` | ffprobe cannot read the file | Re-export the video as H.264/AAC MP4 |
| `415 unsupported_file_type` | Extension is not `.mp4`, `.mov`, or `.mkv` | Convert the file |
| Face detection unavailable | YuNet model or OpenCV missing | Download the model (section 2); jobs still complete with a centred crop |
| Job stuck in `queued` | Worker is disabled or crashed | Check `WORKER_AUTOSTART=true` and the backend log |
| UI cannot reach the API | Backend not running or wrong URL | Start port `8000`; check `frontend/.env.local` |
| Port 3000 already in use | Another dev server is running | Stop it or run `npm.cmd run dev -- -p 3001` and update the origin/CORS if needed |
| Job marked failed after a restart | It was active when the backend stopped | Interrupted jobs are not silently retried; upload again |

Backend logs go to the terminal running uvicorn. Set `LOG_LEVEL=DEBUG` for more
detail. On Windows, Ollama writes its own log to
`%LOCALAPPDATA%\Ollama\server.log`.

---

## 7. Why Ollama sometimes does not respond within 180 seconds

### How the request works

Clip selection is a **non-streaming** `POST /api/chat` to Ollama, one request per
transcript window:

- Transcript windows are `CLIP_WINDOW_SECONDS` long (default **180 s**) with a
  `CLIP_WINDOW_OVERLAP_SECONDS` overlap (default **30 s**).
- Each window asks for up to `CLIP_MAX_CANDIDATES_PER_CHUNK` candidates (default
  **4**) as structured JSON.
- The HTTP client uses a **total per-request timeout** of
  `OLLAMA_TIMEOUT_SECONDS` (default **180 s**). That covers model loading, prompt
  evaluation, and every generated token.
- Requests are sequential. A 10-minute video produces several windows, and each
  one gets its own 180 s budget.
- A malformed JSON response skips that window; a timeout aborts the whole
  selection and fails the job with
  `Ollama did not respond within 180 seconds while selecting clips.`
- There is no automatic retry on timeout.

So "did not respond" usually does not mean Ollama is broken. It means the model
did not finish the whole request inside the budget.

### What we measured on this machine

Reproducing the pipeline with the default model and a short 66 s / 157-word
transcript:

```text
ollama ps
qwen2.5:3b   2.4 GB   100% CPU   8192 context
```

**First request, cold model (180 s timeout):**

- Prompt size: **881 tokens**, no prompt cache
- Model load plus prompt evaluation consumed roughly **100 s**
- Generation ran at about **3.1 tokens/second**
- After 180 s, Ollama had produced only **~229 tokens** and was still generating
  when the client disconnected
- Result: `ollama_timeout` at 84% (`Clip selection failed`)

**Immediate retry, same prompt, warm model (600 s timeout):**

- Prompt cache hit: only **1 token** needed evaluation
- Output: **487 tokens** at **2.84 tokens/second**
- Finished in **175.8 s** and returned 4 valid clips

The warm retry barely fit inside the original 180 s budget. The cold first
request did not. That gap is the whole story: model loading and prompt
evaluation are charged to the same timeout as token generation.

A structured response for four candidates (titles, hooks, reasons, and five
scores each) is ~490 output tokens here, so 180 s is not enough on this CPU once
cold-start work is included. The failed job stored in this repo
(`180dcaff-…`, 66.7 s, 157 words) used a reasoning-distill model,
`huihui_ai/deepseek-r1-abliterated:1.5b`; reasoning models can also spend tokens
"thinking" before emitting JSON, which makes the same budget even tighter.

### Why it is intermittent

The 180 s budget sits right at the edge of what this machine can do:

- **Cold vs. warm model.** The first request after Ollama starts, after
  `OLLAMA_KEEP_ALIVE` expires, or after a model switch pays load time. The same
  request immediately afterwards can reuse the model and the prompt cache and
  finish in time.
- **How many candidates the model proposes.** Two short candidates fit; four
  candidates with longer hooks and reasons may not.
- **CPU contention.** Whisper, FFmpeg, the browser, or another Ollama request
  lowers the token rate and pushes the same request over the limit.

That is why the same video can succeed on one run and fail with `ollama_timeout`
on the next. Raising the timeout and keeping the model warm removes most of this
variance.

**Practical expectation.** At ~3 tokens/second, one successful 3-minute window
takes about 3 minutes when warm. A 10-minute video has roughly four windows, so
clip selection alone can take 10–15 minutes on this CPU. That is slow, but it is
not a hang. Watch the job page progress and the `tg` rate in the Ollama log to
tell the difference.

### Common causes

1. **CPU-only inference.** `ollama ps` shows `100% CPU` when no compatible GPU
   is used. Generation can be a few tokens per second, and structured JSON is
   output-heavy.
2. **Cold start.** The first request pays model load time. `OLLAMA_KEEP_ALIVE`
   defaults to `5m`, so a job that waits in the queue, or runs later, may reload
   the model.
3. **Structured JSON output.** The JSON schema and up to four candidates mean
   hundreds of output tokens. Output tokens are the slow part.
4. **Reasoning models.** R1 distills and similar models may generate hidden
   reasoning even with `OLLAMA_THINK=false`. That option is a request hint, not a
   guarantee for every model.
5. **Large context.** `OLLAMA_NUM_CTX=8192` increases memory use and prompt
   processing. It is not the main cost for a short prompt, but it matters on
   low-memory machines.
6. **Long windows and long videos.** A dense 3-minute window can be thousands of
   tokens, and a long video multiplies the number of windows. Total selection
   time scales with the number of windows.
7. **Memory pressure.** Whisper, FFmpeg, OpenCV, and Ollama compete for RAM.
   Ollama may evict and reload a model, or fall back to slower settings.
8. **Ollama is busy.** Requests are serialized by default
   (`OLLAMA_NUM_PARALLEL=1`). Another client, or a previous request that has not
   fully stopped, can delay the next one.
9. **First-time download.** `ollama pull` may still be downloading, or the model
   may be partially available, when the job starts.

### Confirm what is happening

```powershell
# Is a model loaded, and is it using CPU or GPU?
ollama ps

# Watch load, prompt evaluation, and generation speed.
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 60 -Wait
```

Look for lines like:

```text
slot print_timing: id 0 | task 0 | n_gen = 199, tg = 3.06 t/s
```

`tg` is token generation speed. If it is only a few tokens per second, the
timeout is a hardware/budget problem, not a network problem.

You can also time a single request directly:

```powershell
$body = '{"model":"qwen2.5:3b","stream":false,"messages":[{"role":"user","content":"Reply with the single word ready."}]}'
Measure-Command {
  curl.exe -s http://127.0.0.1:11434/api/chat `
    -H "Content-Type: application/json" `
    -d $body | Out-Null
} | Select-Object TotalSeconds
```

### Fixes, in order of impact

1. **Raise the timeout.** Set `OLLAMA_TIMEOUT_SECONDS=600` (or higher) in
   `backend/.env` and restart the backend. This is the direct fix when the model
   is healthy but slow. Because the timeout is per window, a long video can
   still take many minutes in total.
2. **Keep the model warm.** Set `OLLAMA_KEEP_ALIVE=30m` and preload it before
   uploading:

   ```powershell
   ollama run qwen2.5:3b ""
   ```

   This removes cold-start cost from the first window.
3. **Use a faster, non-reasoning model.** `qwen2.5:1.5b` or `llama3.2:1b` are
   much faster on CPU. Avoid R1 distills for structured JSON unless you have a
   GPU or a generous timeout.
4. **Ask for less output.** Lower `CLIP_MAX_CANDIDATES_PER_CHUNK` to `2`, and
   consider a shorter `CLIP_WINDOW_SECONDS` (for example `120`) so each request
   is smaller. More windows means more requests, so balance the two.
5. **Enable GPU acceleration.** Check that Ollama detects a supported GPU; if
   `ollama ps` always says `100% CPU`, see Ollama's GPU documentation and update
   your drivers. This is usually the largest single speedup.
6. **Reduce memory pressure.** Close other heavy applications, avoid running two
   jobs, and keep `OLLAMA_NUM_CTX` only as large as the prompts need.
7. **Verify the model is fully pulled.** Run `ollama list`; if it is missing,
   `ollama pull qwen2.5:3b` and wait for completion.

### What happens after a timeout

- The job is marked `failed` at `selecting_clips` (progress 84) with the
  timeout message shown on the job page.
- The upload and transcript are kept so you can inspect them; delete the job
  from the UI to remove all of its media.
- The backend stays healthy and the worker moves on to the next queued job.
- Ollama may still show the model loaded, or finish the aborted generation
  briefly, after the client has given up. Its log may show a `500` for the
  `/api/chat` request; that is the client disconnecting at the timeout, not an
  Ollama crash.

### Suggested local settings for a CPU-only 16 GB machine

Put these in `backend/.env` and restart the backend:

```dotenv
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=600
OLLAMA_KEEP_ALIVE=30m
OLLAMA_NUM_CTX=8192
OLLAMA_THINK=false

# Faster smoke tests; remove for better transcription quality.
WHISPER_MODEL=tiny
```

If jobs still time out, switch to `qwen2.5:1.5b` or lower
`CLIP_MAX_CANDIDATES_PER_CHUNK` before raising the timeout further.

---

## 8. Command cheat sheet

| Task | Command |
| --- | --- |
| Start API + worker | `cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| Start UI | `cd frontend; npm.cmd run dev` |
| Build UI | `cd frontend; npm.cmd run build` |
| Run backend tests | `cd backend; .\.venv\Scripts\python.exe -m pytest -q` |
| Health check | `Invoke-RestMethod http://127.0.0.1:8000/api/health` |
| List Ollama models | `ollama list` |
| Show loaded model / device | `ollama ps` |
| Pull default model | `ollama pull qwen2.5:3b` |
| Preload model | `ollama run qwen2.5:3b ""` |
| Tail Ollama log | `Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 60 -Wait` |
| Delete a job via API | `curl.exe -X DELETE http://127.0.0.1:8000/api/jobs/<job-uuid>` |

For the full architecture, API, configuration table, and test coverage, see
[README.md](README.md).
