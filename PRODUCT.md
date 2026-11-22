# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing codebase: Next.js 16 (App Router), React 19, Tailwind CSS 4, TypeScript. Python/FastAPI backend with SQLite, FFmpeg, faster-whisper, and local Ollama. Frontend and backend run as two local processes; the browser talks to `127.0.0.1:8000`.

## Users

Creators, podcasters, and anyone recording long videos on a personal machine who needs short vertical clips without sending files to a cloud service. They work locally, one video at a time, on modest hardware (16 GB, CPU-only), and return to the job page to watch progress, preview clips, and download MP4s.

## Product Purpose

ClipForge turns a long local recording into short 9:16 clips, entirely on the user's machine. Success: the user uploads a source video, the pipeline transcribes it, selects self-contained moments, tracks the likely speaker for portrait framing, renders verified H.264/AAC clips, and the user previews and downloads them. A second tool, Segmenter, trims and joins exact timestamp ranges without AI selection.

## Positioning

No cloud processing, no accounts, no per-minute fees: transcription, selection, tracking, and rendering all happen on the user's computer. The UI is honest about heuristics — speaker tracking is labelled as heuristic, clip score is a ranking aid, and every fallback crop is called out rather than presented as successful tracking.

## Operating Context

Desktop browser on the same machine as the backend. Long-running jobs are monitored by polling; tabs may be closed and reopened. Users upload one file at a time, cancel or delete jobs, and keep rendered clips on disk until they delete them. The job page doubles as the results page.

## Capabilities and Constraints

- Two tools: AI Clipper (upload + optional speaker tracking) and Segmenter (timestamp ranges, separate or joined, original or centred 9:16 frame).
- Segmenter uses source projects: upload once, then queue any number of independent cut jobs against the same stored video, with a per-project cut history.
- Job states: queued → inspecting → transcribing → selecting_clips → tracking_speakers → rendering → completed | failed | cancelled.
- Clips stream inline for preview and download as `?download=true` attachments; files are only exposed after render verification.
- Captions, music, text, and watermarks are intentionally not generated.
- One job at a time; CPU-only rendering; uploads up to a configured limit (5 GiB default).
- Backend is unauthenticated and bound to localhost; do not expose it to an untrusted network.

## Brand Commitments

Name: **ClipForge**. Voice: plain, precise, non-hype — states what the tool did and calls out uncertainty. No invented capability, testimonial, virality claim, or cloud promise.

User-pinned visual direction for this redesign (recorded without expanding it): **Lighter Workshop** — warm off-white workspace, ink-black type, a single signal accent, editorial light-mode tool. The rejected alternative was a dark "Studio Deck" suite.

## Evidence on Hand

`README.md` documents the full pipeline, API, states, and verified live checks. `RUNNING.md` covers setup. Existing Next.js UI in `frontend/src/` (landing, segmenter, job results, 404) supplies real copy, labels, and states. Sample media `test_vid.mp4` exists at the repository root.

## Product Principles

1. Local-first is a promise, not a feature flag — never imply cloud processing or accounts.
2. Show the machine's actual state; a fallback crop or heuristic score must never be dressed as a success.
3. Keep the user oriented during long jobs: stage, progress, and what happens next are always visible.
4. One task at a time, done honestly: upload, inspect, cut, preview, download.
5. Respect the machine — CPU-first defaults, bounded concurrency, explicit cancellation and cleanup.

## Accessibility & Inclusion

Keyboard-reachable upload dropzones, labelled controls, visible focus, and readable contrast on paper surfaces. Job status is exposed with `aria-live`; reduced-motion preference disables progress sheen and transitions.
