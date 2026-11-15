# Graph Report - clipforge  (2026-11-15)

## Corpus Check
- 77 files · ~49,082 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .example 2, (none) 2, .css 1)

## Summary
- 1064 nodes · 3071 edges · 55 communities (38 shown, 17 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 374 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c9c4b9fc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FFmpeg Clip Rendering
- Config Validation Tests
- Settings
- Transcription Segments
- Health API Checks
- pipeline.py
- Cancellation and Work
- Frontend UI Components
- Worker Pipeline Services
- FFmpeg Command Helpers
- score_candidate
- Clip Selection Schemas
- Transcript Chunking
- Ollama Selection Client
- Face Detection Core
- Frontend Dependencies
- App Shell Layout
- Crop Plan Geometry
- Transcript Segment Fitting
- Face Tracking Frames
- Speaker Tracking Results
- routes_upload.py
- Media Probe Service
- FaceTrack
- Service Config Modules
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- models/job.py
- test_hardening.py
- Clip Candidate Scoring
- Project Docs Concepts
- Job API Operations
- Segmenter UI Flow
- Frontend API Client
- Ollama Client Probe
- speaker_tracking.py
- Job Read Schemas
- Clip Selection Logic
- API Shared Types
- Tracker Orchestration Test
- PostCSS Config
- Backend Package Meta

## God Nodes (most connected - your core abstractions)
1. `Settings` - 177 edges
2. `process_job()` - 41 edges
3. `Job` - 38 edges
4. `create_app()` - 37 edges
5. `JobState` - 34 edges
6. `Transcript` - 33 edges
7. `utc_now()` - 32 edges
8. `probe_media()` - 31 edges
9. `JobStatusView()` - 31 edges
10. `create_job()` - 28 edges

## Surprising Connections (you probably didn't know these)
- `test_job_state_cancelled_is_terminal()` --uses--> `JobState`  [INFERRED]
  backend/tests/test_hardening.py → backend/app/models/job.py
- `Frontend Next.js agent guidance` --conceptually_related_to--> `API and results experience`  [INFERRED]
  frontend/AGENTS.md → README.md
- `Clip selection prompt template` --rationale_for--> `LLM clip selection via Ollama`  [INFERRED]
  backend/app/prompts/clip_selection.txt → README.md
- `Pinned backend dependency set` --conceptually_related_to--> `Portrait clip rendering with FFmpeg`  [INFERRED]
  backend/requirements.lock.txt → README.md
- `Pinned backend dependency set` --conceptually_related_to--> `Heuristic speaker tracking and crop planning`  [INFERRED]
  backend/requirements.lock.txt → README.md

## Import Cycles
- 2-file cycle: `backend/app/db.py -> backend/app/models/clip.py -> backend/app/db.py`
- 2-file cycle: `backend/app/db.py -> backend/app/models/job.py -> backend/app/db.py`

## Communities (55 total, 17 thin omitted)

### Community 0 - "FFmpeg Clip Rendering"
Cohesion: 0.10
Nodes (24): MediaInfo, build_crop_commands_file(), _even(), FFmpegClipRenderer, format_sendcmd_path(), RenderingError, _verify_output(), _media_info() (+16 more)

### Community 1 - "Config Validation Tests"
Cohesion: 0.08
Nodes (31): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+23 more)

### Community 2 - "Settings"
Cohesion: 0.07
Nodes (29): get_settings(), Settings, create_app(), cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), RenderResult (+21 more)

### Community 3 - "Transcription Segments"
Cohesion: 0.07
Nodes (26): SegmentGroup, build_transcript(), _clamp(), FasterWhisperTranscriber, _finite_float(), is_non_speech_text(), load_transcript(), _load_whisper_model() (+18 more)

### Community 4 - "Health API Checks"
Cohesion: 0.10
Nodes (16): health(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), lifespan(), HealthCheck, HealthLimits (+8 more)

### Community 5 - "pipeline.py"
Cohesion: 0.13
Nodes (16): _apply_progress(), process_segmenter_job(), Transcriber, job_clips_dir(), job_work_dir(), relative_to_data_dir(), utc_now(), _check_cancelled() (+8 more)

### Community 6 - "Cancellation and Work"
Cohesion: 0.14
Nodes (9): CancelToken, apply_progress(), _raise_if_cancelled(), _select_clips_with_progress(), on_progress(), on_progress(), on_stage(), test_process_job_marks_preexisting_cancellation() (+1 more)

### Community 7 - "Frontend UI Components"
Cohesion: 0.13
Nodes (29): JobPage(), AlertIcon(), CheckIcon(), CopyIcon(), DownloadIcon(), SpinnerIcon(), TrashIcon(), XIcon() (+21 more)

### Community 8 - "Worker Pipeline Services"
Cohesion: 0.09
Nodes (4): ClipSelector, ClipRenderer, SpeakerTracker, JobWorker

### Community 9 - "FFmpeg Command Helpers"
Cohesion: 0.11
Nodes (9): sample_clip_frames(), extract_audio(), unload_whisper_models(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command() (+1 more)

### Community 10 - "score_candidate"
Cohesion: 0.24
Nodes (6): build_response_schema(), _conciseness(), _finite_float(), _normalized_score(), score_candidate(), test_response_schema_requires_clip_fields()

### Community 11 - "Clip Selection Schemas"
Cohesion: 0.17
Nodes (17): LLMClip, LLMClipScores, LLMClipSelection, build_chunks(), candidates_from_payload(), TranscriptChunk, _payload(), _segment() (+9 more)

### Community 12 - "Transcript Chunking"
Cohesion: 0.12
Nodes (15): TranscriptSegment, TranscriptWord, build_candidate(), _clamp(), _clean_text(), _fit_segment_range(), fits_hard(), fits_target() (+7 more)

### Community 13 - "Ollama Selection Client"
Cohesion: 0.13
Nodes (14): Transcript, OllamaClipSelector, OllamaError, OllamaMalformedResponse, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama(), test_selector_returns_empty_when_every_chunk_is_malformed() (+6 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.13
Nodes (4): create_face_detector(), FaceDetector, OpenCVYuNetDetector, test_missing_face_model_raises_actionable_error()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.14
Nodes (16): nextConfig, metadata, RootLayout(), viewport, NotFound(), AppShell(), NavItem, navItems (+8 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.17
Nodes (9): FaceBox, _association_score(), build_crop_plan(), _centrality(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres() (+1 more)

### Community 18 - "Transcript Segment Fitting"
Cohesion: 0.19
Nodes (11): _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), _render_range(), _run_ffmpeg() (+3 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.14
Nodes (18): assign_mouth_motion(), build_face_tracks(), build_speech_intervals(), compute_crop_geometry(), CropGeometry, FrameFace, FrameFaces, _face() (+10 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): FaceDetectionError, build_centered_result(), _extract_mouth_patch(), _load_frame(), OpenCVSpeakerTracker, _report(), SpeakerTrackingResult, _to_grayscale() (+3 more)

### Community 21 - "routes_upload.py"
Cohesion: 0.06
Nodes (21): get_session(), api_error(), get_clip(), get_clip_file(), _get_clip_or_404(), create_job(), reject_oversized_upload(), EmptyUpload (+13 more)

### Community 23 - "Media Probe Service"
Cohesion: 0.21
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 25 - "Service Config Modules"
Cohesion: 0.15
Nodes (3): _configure_logging(), _model_is_available(), _normalize_model_name()

### Community 27 - "Landing Page UI"
Cohesion: 0.17
Nodes (16): AIClipperPage(), features, pipeline, ArrowRightIcon(), CpuIcon(), FileVideoIcon(), ShieldIcon(), FALLBACK_FORMATS (+8 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.21
Nodes (9): Job, JobState, claim_next_queued_job(), recover_interrupted_jobs(), _job(), test_claim_next_queued_job_marks_inspecting(), test_job_state_helpers(), test_progress_never_moves_backwards() (+1 more)

### Community 30 - "models/job.py"
Cohesion: 0.18
Nodes (4): _apply_sqlite_additive_migrations(), Base, Clip, test_additive_migration_adds_phase4_clip_columns()

### Community 31 - "test_hardening.py"
Cohesion: 0.10
Nodes (16): delete_job_files(), JobCancelled, BlockingTranscriber, _clip_row(), _job_dirs(), _job_row(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_clip_file_endpoint_rejects_unsafe_stored_path() (+8 more)

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.25
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.16
Nodes (7): delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips(), ClipRead, resolve_stored_path()

### Community 36 - "Segmenter UI Flow"
Cohesion: 0.25
Nodes (11): SegmenterPage(), ScissorsIcon(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady(), SegmenterForm(), handleDrop(), handleInputChange() (+3 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.37
Nodes (12): API_BASE_URL, ApiError, createSegmenterJob(), deleteJob(), errorFromResponse(), getHealth(), getJob(), getJobClips() (+4 more)

### Community 40 - "speaker_tracking.py"
Cohesion: 0.12
Nodes (15): _centered_plan(), choose_active_tracks(), _clamp(), _clamp_center(), CropPlan, CropSample, interpolate_crop(), is_speech_active() (+7 more)

### Community 42 - "Clip Selection Logic"
Cohesion: 0.20
Nodes (5): ClipSelectionError, load_prompt_template(), render_prompt(), _settings(), test_prompt_placeholder_error_is_actionable()

### Community 44 - "API Shared Types"
Cohesion: 0.25
Nodes (7): Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind

### Community 48 - "Tracker Orchestration Test"
Cohesion: 0.33
Nodes (3): SampledFrame, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 347 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `FFmpeg Clip Rendering`, `Config Validation Tests`, `Transcription Segments`, `Health API Checks`, `pipeline.py`, `Cancellation and Work`, `Worker Pipeline Services`, `FFmpeg Command Helpers`, `score_candidate`, `Clip Selection Schemas`, `Transcript Chunking`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `Transcript Segment Fitting`, `Face Tracking Frames`, `Speaker Tracking Results`, `routes_upload.py`, `Media Probe Service`, `Service Config Modules`, `Job and Clip Models`, `models/job.py`, `test_hardening.py`, `Clip Candidate Scoring`, `Job API Operations`, `Ollama Client Probe`, `speaker_tracking.py`, `Clip Selection Logic`, `Tracker Orchestration Test`?**
  _High betweenness centrality (0.290) - this node is a cross-community bridge._
- **Are the 115 inferred relationships involving `Settings` (e.g. with `health()` and `create_job()`) actually correct?**
  _`Settings` has 115 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FFmpeg Clip Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.09797979797979799 - nodes in this community are weakly interconnected._
- **Why does `Transcript` connect `Ollama Selection Client` to `Config Validation Tests`, `Job API Operations`, `Transcription Segments`, `pipeline.py`, `Cancellation and Work`, `Worker Pipeline Services`, `speaker_tracking.py`, `FFmpeg Command Helpers`, `Clip Selection Schemas`, `Transcript Chunking`, `Speaker Tracking Results`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `process_job()` (e.g. with `Settings` and `Job`) actually correct?**
  _`process_job()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `Config Validation Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.08456659619450317 - nodes in this community are weakly interconnected._