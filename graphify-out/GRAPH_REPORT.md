# Graph Report - clipforge  (2026-11-17)

## Corpus Check
- 80 files · ~51,246 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1107 nodes · 3104 edges · 67 communities (43 shown, 24 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 325 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a7fa138`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FFmpeg Clip Rendering
- test_upload_jobs.py
- conftest.py
- test_transcript.py
- main.py
- process_job
- db.py
- Frontend UI Components
- Settings
- FFmpeg Command Helpers
- services/clip_selection.py
- Clip Selection Schemas
- TranscriptSegment
- Ollama Selection Client
- Face Detection Core
- Frontend Dependencies
- App Shell Layout
- Crop Plan Geometry
- Transcript Segment Fitting
- Face Tracking Frames
- Speaker Tracking Results
- pathlib
- Media Probe Service
- FaceTrack
- rendering.py
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- pipeline.py
- test_hardening.py
- Clip Candidate Scoring
- Project Docs Concepts
- Job API Operations
- Segmenter UI Flow
- Frontend API Client
- Ollama Client Probe
- speaker_tracking.py
- Clip Selection Logic
- command_exists
- Design System: ClipForge
- routes_clips.py
- transcription.py
- PostCSS Config
- Backend Package Meta
- JobKind
- create_job
- .render_clip
- SampledFrame
- Product
- routes_upload.py

## God Nodes (most connected - your core abstractions)
1. `Settings` - 176 edges
2. `Job` - 38 edges
3. `create_app()` - 37 edges
4. `process_job()` - 37 edges
5. `JobState` - 34 edges
6. `JobStatusView()` - 33 edges
7. `Transcript` - 33 edges
8. `utc_now()` - 32 edges
9. `probe_media()` - 31 edges
10. `FaceBox` - 27 edges

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
- 2-file cycle: `backend/app/db.py -> backend/app/models/job.py -> backend/app/db.py`
- 2-file cycle: `backend/app/db.py -> backend/app/models/clip.py -> backend/app/db.py`

## Communities (67 total, 24 thin omitted)

### Community 0 - "FFmpeg Clip Rendering"
Cohesion: 0.12
Nodes (22): MediaInfo, build_crop_commands_file(), FFmpegClipRenderer, format_sendcmd_path(), RenderingError, _verify_output(), _media_info(), _require_ffmpeg() (+14 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.09
Nodes (30): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+22 more)

### Community 2 - "conftest.py"
Cohesion: 0.28
Nodes (13): get_settings(), create_app(), app(), failing_client(), failing_renderer_client(), failing_selector_client(), failing_tracker_client(), no_speech_client() (+5 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.08
Nodes (25): SegmentGroup, build_transcript(), _clamp(), _finite_float(), is_non_speech_text(), load_transcript(), _load_whisper_model(), _report() (+17 more)

### Community 4 - "main.py"
Cohesion: 0.14
Nodes (13): health(), _configure_logging(), lifespan(), HealthCheck, HealthLimits, HealthResponse, check_face_detection(), check_media_tools() (+5 more)

### Community 5 - "process_job"
Cohesion: 0.11
Nodes (17): CancelToken, utc_now(), apply_progress(), _check_cancelled(), _mark_cancelled(), _mark_failed(), process_job(), _raise_if_cancelled() (+9 more)

### Community 6 - "db.py"
Cohesion: 0.17
Nodes (6): _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), test_additive_migration_adds_phase4_clip_columns()

### Community 7 - "Frontend UI Components"
Cohesion: 0.15
Nodes (26): JobPage(), AlertIcon(), DownloadIcon(), SpinnerIcon(), badgeClasses(), ClipCard(), Detail(), ErrorState() (+18 more)

### Community 8 - "Settings"
Cohesion: 0.10
Nodes (6): Settings, cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), ensure_data_dirs()

### Community 9 - "FFmpeg Command Helpers"
Cohesion: 0.11
Nodes (10): sample_clip_frames(), extract_audio(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate() (+2 more)

### Community 10 - "services/clip_selection.py"
Cohesion: 0.13
Nodes (16): TranscriptWord, build_candidate(), build_response_schema(), candidates_from_payload(), _clamp(), _clean_text(), _conciseness(), _finite_float() (+8 more)

### Community 11 - "Clip Selection Schemas"
Cohesion: 0.16
Nodes (19): LLMClip, LLMClipScores, LLMClipSelection, render_prompt(), TranscriptChunk, _payload(), _segment(), _settings() (+11 more)

### Community 12 - "TranscriptSegment"
Cohesion: 0.19
Nodes (5): TranscriptSegment, _fit_segment_range(), fits_hard(), fits_target(), _range_duration()

### Community 13 - "Ollama Selection Client"
Cohesion: 0.14
Nodes (13): OllamaClipSelector, OllamaError, OllamaMalformedResponse, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama(), test_selector_returns_empty_when_every_chunk_is_malformed(), test_selector_skips_malformed_chunk_and_keeps_valid_one() (+5 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.13
Nodes (4): create_face_detector(), FaceDetector, OpenCVYuNetDetector, test_missing_face_model_raises_actionable_error()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.09
Nodes (19): nextConfig, archivo, metadata, robotoMono, RootLayout(), viewport, AppShell(), NavItem (+11 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.17
Nodes (9): FaceBox, _association_score(), build_crop_plan(), _centrality(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres() (+1 more)

### Community 18 - "Transcript Segment Fitting"
Cohesion: 0.16
Nodes (13): _apply_progress(), _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), process_segmenter_job() (+5 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.14
Nodes (18): assign_mouth_motion(), build_face_tracks(), build_speech_intervals(), compute_crop_geometry(), CropGeometry, FrameFace, FrameFaces, _face() (+10 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): FaceDetectionError, build_centered_result(), _extract_mouth_patch(), _load_frame(), OpenCVSpeakerTracker, _report(), SpeakerTrackingResult, _to_grayscale() (+3 more)

### Community 21 - "pathlib"
Cohesion: 0.15
Nodes (13): reject_oversized_upload(), EmptyUpload, file_extension(), human_size(), remove_tree(), stream_upload_to_path(), UploadTooLarge, test_file_extension_is_lowercase() (+5 more)

### Community 23 - "Media Probe Service"
Cohesion: 0.23
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 25 - "rendering.py"
Cohesion: 0.15
Nodes (3): _model_is_available(), _normalize_model_name(), _even()

### Community 27 - "Landing Page UI"
Cohesion: 0.22
Nodes (14): CheckIcon(), FileVideoIcon(), UploadCloudIcon(), XIcon(), FALLBACK_FORMATS, mediaToolsReady(), toolProblem(), UploadForm() (+6 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.20
Nodes (9): Job, JobState, claim_next_queued_job(), recover_interrupted_jobs(), _job(), test_claim_next_queued_job_marks_inspecting(), test_job_state_helpers(), test_progress_never_moves_backwards() (+1 more)

### Community 30 - "pipeline.py"
Cohesion: 0.14
Nodes (9): Base, Clip, delete_job_files(), job_clips_dir(), job_upload_dir(), job_work_dir(), relative_to_data_dir(), resolve_stored_path() (+1 more)

### Community 31 - "test_hardening.py"
Cohesion: 0.10
Nodes (17): JobCancelled, client(), BlockingTranscriber, _clip_row(), _job_dirs(), _job_row(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_clip_file_endpoint_rejects_unsafe_stored_path() (+9 more)

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.19
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.26
Nodes (5): delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips()

### Community 36 - "Segmenter UI Flow"
Cohesion: 0.19
Nodes (16): NotFound(), AIClipperPage(), steps, SegmenterPage(), specimens, ArrowRightIcon(), RegMarks(), ScissorsIcon() (+8 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.18
Nodes (17): handleSubmit(), API_BASE_URL, ApiError, createSegmenterJob(), errorFromResponse(), getJob(), getJobClips(), messageFromDetail() (+9 more)

### Community 40 - "speaker_tracking.py"
Cohesion: 0.12
Nodes (15): _centered_plan(), choose_active_tracks(), _clamp(), _clamp_center(), CropPlan, CropSample, interpolate_crop(), is_speech_active() (+7 more)

### Community 42 - "Clip Selection Logic"
Cohesion: 0.20
Nodes (3): build_chunks(), ClipSelectionError, load_prompt_template()

### Community 44 - "command_exists"
Cohesion: 0.47
Nodes (6): command_exists(), audio_only_file(), _ffmpeg_command(), long_sample_video(), sample_video(), video_without_audio()

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "routes_clips.py"
Cohesion: 0.20
Nodes (4): get_clip(), get_clip_file(), _get_clip_or_404(), ClipRead

### Community 48 - "transcription.py"
Cohesion: 0.07
Nodes (9): Transcript, ClipSelector, ClipRenderer, SpeakerTracker, FasterWhisperTranscriber, save_transcript(), Transcriber, unload_whisper_models() (+1 more)

### Community 58 - "create_job"
Cohesion: 0.17
Nodes (3): create_job(), sanitize_display_filename(), test_sanitize_display_filename()

### Community 60 - "SampledFrame"
Cohesion: 0.33
Nodes (3): SampledFrame, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 386 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `FFmpeg Clip Rendering`, `test_upload_jobs.py`, `conftest.py`, `test_transcript.py`, `main.py`, `process_job`, `db.py`, `FFmpeg Command Helpers`, `services/clip_selection.py`, `Clip Selection Schemas`, `TranscriptSegment`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `Transcript Segment Fitting`, `Face Tracking Frames`, `Speaker Tracking Results`, `pathlib`, `Media Probe Service`, `rendering.py`, `Job and Clip Models`, `pipeline.py`, `test_hardening.py`, `Clip Candidate Scoring`, `Ollama Client Probe`, `speaker_tracking.py`, `command_exists`, `transcription.py`, `create_job`, `.render_clip`, `SampledFrame`, `routes_upload.py`?**
  _High betweenness centrality (0.250) - this node is a cross-community bridge._
- **Are the 104 inferred relationships involving `Settings` (e.g. with `health()` and `_configure_logging()`) actually correct?**
  _`Settings` has 104 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FFmpeg Clip Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.1214574898785425 - nodes in this community are weakly interconnected._
- **Why does `FaceBox` connect `Crop Plan Geometry` to `conftest.py`, `speaker_tracking.py`, `Face Detection Core`, `Face Tracking Frames`, `Speaker Tracking Results`, `FaceTrack`, `rendering.py`, `SampledFrame`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Job` (e.g. with `delete_job()` and `get_job()`) actually correct?**
  _`Job` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08748615725359911 - nodes in this community are weakly interconnected._