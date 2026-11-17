# Graph Report - clipforge  (2026-11-15)

## Corpus Check
- 77 files · ~49,082 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .example 2, (none) 2, .css 1)

## Summary
- 1068 nodes · 3055 edges · 65 communities (42 shown, 23 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 328 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d2fa221d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FFmpeg Clip Rendering
- test_upload_jobs.py
- Settings
- Transcription Segments
- routes_health.py
- pipeline.py
- Cancellation and Work
- Frontend UI Components
- Worker Pipeline Services
- FFmpeg Command Helpers
- services/clip_selection.py
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
- speaker_tracking.py
- face_detection.py
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- routes_upload.py
- test_hardening.py
- Clip Candidate Scoring
- Project Docs Concepts
- Job API Operations
- Segmenter UI Flow
- Frontend API Client
- Ollama Client Probe
- interpolate_crop
- Clip Selection Logic
- API Shared Types
- pytest
- tooling.py
- ClipSelector
- PostCSS Config
- Backend Package Meta
- create_session_factory
- main.py
- .render_clip

## God Nodes (most connected - your core abstractions)
1. `Settings` - 176 edges
2. `Job` - 38 edges
3. `process_job()` - 37 edges
4. `create_app()` - 37 edges
5. `JobState` - 34 edges
6. `Transcript` - 33 edges
7. `utc_now()` - 32 edges
8. `JobStatusView()` - 31 edges
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
- 2-file cycle: `backend/app/db.py -> backend/app/models/clip.py -> backend/app/db.py`
- 2-file cycle: `backend/app/db.py -> backend/app/models/job.py -> backend/app/db.py`

## Communities (65 total, 23 thin omitted)

### Community 0 - "FFmpeg Clip Rendering"
Cohesion: 0.14
Nodes (20): MediaInfo, build_crop_commands_file(), FFmpegClipRenderer, RenderingError, _verify_output(), _media_info(), _require_ffmpeg(), test_build_crop_commands_centers_without_plan() (+12 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.15
Nodes (12): test_clip_file_requires_completed_render(), test_clip_list_is_empty_in_phase_one(), test_long_video_produces_candidate_clips(), test_rendering_failure_marks_clip_failed(), test_tracking_failure_keeps_job_and_centres_crop(), test_upload_rejects_file_without_video_stream(), test_valid_upload_creates_queued_job_and_worker_completes(), test_worker_marks_no_speech_transcript_completed() (+4 more)

### Community 2 - "Settings"
Cohesion: 0.06
Nodes (38): get_settings(), Settings, create_engine_from_settings(), ensure_sqlite_directory(), create_app(), cleanup_orphan_job_dirs(), is_job_uuid(), job_directories() (+30 more)

### Community 3 - "Transcription Segments"
Cohesion: 0.07
Nodes (29): Transcript, build_transcript(), _clamp(), extract_audio(), FasterWhisperTranscriber, _finite_float(), is_non_speech_text(), load_transcript() (+21 more)

### Community 4 - "routes_health.py"
Cohesion: 0.30
Nodes (5): health(), HealthCheck, HealthLimits, HealthResponse, check_ollama()

### Community 5 - "pipeline.py"
Cohesion: 0.12
Nodes (16): _apply_progress(), process_segmenter_job(), SpeakerTracker, job_clips_dir(), job_upload_dir(), job_work_dir(), relative_to_data_dir(), resolve_stored_path() (+8 more)

### Community 6 - "Cancellation and Work"
Cohesion: 0.15
Nodes (8): CancelToken, _raise_if_cancelled(), _select_clips_with_progress(), on_progress(), _transcribe_with_progress(), on_progress(), on_stage(), test_process_job_marks_preexisting_cancellation()

### Community 7 - "Frontend UI Components"
Cohesion: 0.13
Nodes (29): JobPage(), AlertIcon(), CheckIcon(), CopyIcon(), DownloadIcon(), SpinnerIcon(), TrashIcon(), XIcon() (+21 more)

### Community 9 - "FFmpeg Command Helpers"
Cohesion: 0.13
Nodes (8): _even(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate(), fake_run()

### Community 10 - "services/clip_selection.py"
Cohesion: 0.16
Nodes (14): build_candidate(), build_response_schema(), _clamp(), _clean_text(), _conciseness(), _finite_float(), _normalized_score(), _report() (+6 more)

### Community 11 - "Clip Selection Schemas"
Cohesion: 0.19
Nodes (16): LLMClip, LLMClipScores, build_chunks(), candidates_from_payload(), TranscriptChunk, _payload(), _segment(), test_boundaries_expand_across_segments() (+8 more)

### Community 12 - "Transcript Chunking"
Cohesion: 0.12
Nodes (7): LLMClipSelection, TranscriptSegment, TranscriptWord, _fit_segment_range(), fits_hard(), fits_target(), _range_duration()

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
Cohesion: 0.14
Nodes (16): nextConfig, metadata, RootLayout(), viewport, NotFound(), AppShell(), NavItem, navItems (+8 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.12
Nodes (12): FaceBox, _association_score(), build_crop_plan(), _centrality(), summarize_choices(), TrackChoice, _FakeDetector, test_crop_plan_interpolates_between_samples() (+4 more)

### Community 18 - "Transcript Segment Fitting"
Cohesion: 0.17
Nodes (12): _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), _render_range(), _run_ffmpeg() (+4 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.18
Nodes (15): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, _face(), _frame(), test_exact_portrait_source_is_not_cropped() (+7 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 21 - "routes_upload.py"
Cohesion: 0.06
Nodes (21): api_error(), get_clip(), get_clip_file(), _get_clip_or_404(), create_job(), reject_oversized_upload(), ClipRead, EmptyUpload (+13 more)

### Community 23 - "Media Probe Service"
Cohesion: 0.21
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 24 - "speaker_tracking.py"
Cohesion: 0.20
Nodes (10): choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, FrameFaces, is_speech_active(), _median(), _track_stats() (+2 more)

### Community 25 - "face_detection.py"
Cohesion: 0.15
Nodes (7): FaceDetectionError, sample_clip_frames(), SampledFrame, OpenCVSpeakerTracker, test_tracker_orchestration_builds_a_crop_plan(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

### Community 27 - "Landing Page UI"
Cohesion: 0.17
Nodes (16): AIClipperPage(), features, pipeline, ArrowRightIcon(), CpuIcon(), FileVideoIcon(), ShieldIcon(), FALLBACK_FORMATS (+8 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.18
Nodes (11): Job, JobState, utc_now(), apply_progress(), claim_next_queued_job(), recover_interrupted_jobs(), _job(), test_claim_next_queued_job_marks_inspecting() (+3 more)

### Community 30 - "routes_upload.py"
Cohesion: 0.10
Nodes (4): get_session(), Base, JobKind, JobRead

### Community 31 - "test_hardening.py"
Cohesion: 0.10
Nodes (12): Clip, delete_job_files(), JobCancelled, BlockingTranscriber, _clip_row(), _job_row(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_completed_job_removes_record_clips_and_media() (+4 more)

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
Cohesion: 0.25
Nodes (11): SegmenterPage(), ScissorsIcon(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady(), SegmenterForm(), handleDrop(), handleInputChange() (+3 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.37
Nodes (12): API_BASE_URL, ApiError, createSegmenterJob(), deleteJob(), errorFromResponse(), getHealth(), getJob(), getJobClips() (+4 more)

### Community 39 - "Ollama Client Probe"
Cohesion: 0.15
Nodes (4): _model_is_available(), _normalize_model_name(), OllamaClient, OllamaProbe

### Community 40 - "interpolate_crop"
Cohesion: 0.20
Nodes (4): CropPlan, CropSample, interpolate_crop(), SpeakerTrackingError

### Community 42 - "Clip Selection Logic"
Cohesion: 0.19
Nodes (6): ClipSelectionError, load_prompt_template(), render_prompt(), _settings(), test_prompt_contains_absolute_timestamps_and_limits(), test_prompt_placeholder_error_is_actionable()

### Community 44 - "API Shared Types"
Cohesion: 0.25
Nodes (7): Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind

### Community 45 - "pytest"
Cohesion: 0.23
Nodes (16): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+8 more)

### Community 46 - "tooling.py"
Cohesion: 0.26
Nodes (6): check_face_detection(), check_media_tools(), _check_tool(), check_whisper(), media_tools_available(), ToolCheck

### Community 48 - "ClipSelector"
Cohesion: 0.18
Nodes (3): ClipSelector, ClipRenderer, Transcriber

### Community 57 - "create_session_factory"
Cohesion: 0.24
Nodes (4): _apply_sqlite_additive_migrations(), create_session_factory(), init_db(), test_additive_migration_adds_phase4_clip_columns()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 352 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `FFmpeg Clip Rendering`, `test_upload_jobs.py`, `Transcription Segments`, `routes_health.py`, `pipeline.py`, `Cancellation and Work`, `Worker Pipeline Services`, `FFmpeg Command Helpers`, `services/clip_selection.py`, `Clip Selection Schemas`, `Transcript Chunking`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `Transcript Segment Fitting`, `Face Tracking Frames`, `Speaker Tracking Results`, `routes_upload.py`, `Media Probe Service`, `speaker_tracking.py`, `face_detection.py`, `Job and Clip Models`, `routes_upload.py`, `test_hardening.py`, `Clip Candidate Scoring`, `Ollama Client Probe`, `Clip Selection Logic`, `pytest`, `tooling.py`, `ClipSelector`, `main.py`, `.render_clip`, `config.py`?**
  _High betweenness centrality (0.275) - this node is a cross-community bridge._
- **Are the 104 inferred relationships involving `Settings` (e.g. with `health()` and `_configure_logging()`) actually correct?**
  _`Settings` has 104 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FFmpeg Clip Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.1361344537815126 - nodes in this community are weakly interconnected._
- **Why does `JobWorker` connect `Worker Pipeline Services` to `Settings`, `pipeline.py`, `Cancellation and Work`, `ClipSelector`, `main.py`, `Job and Clip Models`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Job` (e.g. with `delete_job()` and `get_job()`) actually correct?**
  _`Job` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14761904761904762 - nodes in this community are weakly interconnected._