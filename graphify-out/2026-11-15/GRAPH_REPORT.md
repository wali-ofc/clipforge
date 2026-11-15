# Graph Report - clipforge  (2026-11-15)

## Corpus Check
- Corpus is ~49,039 words - fits in a single context window. You may not need a graph.

## Summary
- 1057 nodes · 3079 edges · 57 communities (41 shown, 16 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 384 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- FFmpeg Clip Rendering
- Config Validation Tests
- App Settings Paths
- Transcription Segments
- Health API Checks
- Clip Model Storage
- Cancellation and Work
- Frontend UI Components
- Worker Pipeline Services
- FFmpeg Command Helpers
- Test Stubs and Mocks
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
- Clip API Endpoints
- Upload and File Utils
- Media Probe Service
- Face Track State
- Service Config Modules
- Upload Streaming Helpers
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- Database Setup
- Job Cleanup and Tests
- Clip Candidate Scoring
- Project Docs Concepts
- Transcript Processing
- Job API Operations
- Segmenter UI Flow
- Frontend API Client
- Transcript Schema Models
- Ollama Client Probe
- Crop Plan Schemas
- Job Read Schemas
- Clip Selection Logic
- Cancellation Errors
- API Shared Types
- Request Dependencies
- Frame Sampling
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
- `Pinned backend dependency set` --conceptually_related_to--> `Local transcription with faster-whisper`  [INFERRED]
  backend/requirements.lock.txt → README.md
- `Clip selection prompt template` --rationale_for--> `LLM clip selection via Ollama`  [INFERRED]
  backend/app/prompts/clip_selection.txt → README.md
- `Pinned backend dependency set` --conceptually_related_to--> `Heuristic speaker tracking and crop planning`  [INFERRED]
  backend/requirements.lock.txt → README.md
- `Pinned backend dependency set` --conceptually_related_to--> `Portrait clip rendering with FFmpeg`  [INFERRED]
  backend/requirements.lock.txt → README.md

## Import Cycles
- 2-file cycle: `backend/app/db.py -> backend/app/models/clip.py -> backend/app/db.py`
- 2-file cycle: `backend/app/db.py -> backend/app/models/job.py -> backend/app/db.py`

## Communities (57 total, 16 thin omitted)

### Community 0 - "FFmpeg Clip Rendering"
Cohesion: 0.10
Nodes (24): MediaInfo, build_crop_commands_file(), _even(), FFmpegClipRenderer, format_sendcmd_path(), RenderingError, _verify_output(), _media_info() (+16 more)

### Community 1 - "Config Validation Tests"
Cohesion: 0.09
Nodes (28): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+20 more)

### Community 2 - "App Settings Paths"
Cohesion: 0.09
Nodes (11): Settings, cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), ensure_data_dirs(), client(), _job_dirs() (+3 more)

### Community 3 - "Transcription Segments"
Cohesion: 0.09
Nodes (23): SegmentGroup, build_transcript(), _clamp(), _finite_float(), is_non_speech_text(), load_transcript(), _load_whisper_model(), _sanitize_segment() (+15 more)

### Community 4 - "Health API Checks"
Cohesion: 0.12
Nodes (16): health(), get_settings(), _configure_logging(), create_app(), lifespan(), HealthCheck, HealthLimits, HealthResponse (+8 more)

### Community 5 - "Clip Model Storage"
Cohesion: 0.12
Nodes (9): Base, Clip, ClipRead, job_clips_dir(), relative_to_data_dir(), resolve_stored_path(), utc_now(), _replace_clips() (+1 more)

### Community 6 - "Cancellation and Work"
Cohesion: 0.11
Nodes (17): CancelToken, job_work_dir(), apply_progress(), _check_cancelled(), _cleanup_temp_files(), _mark_cancelled(), _mark_failed(), process_job() (+9 more)

### Community 7 - "Frontend UI Components"
Cohesion: 0.13
Nodes (29): JobPage(), AlertIcon(), CheckIcon(), CopyIcon(), DownloadIcon(), SpinnerIcon(), TrashIcon(), XIcon() (+21 more)

### Community 8 - "Worker Pipeline Services"
Cohesion: 0.08
Nodes (5): ClipSelector, ClipRenderer, SpeakerTracker, Transcriber, JobWorker

### Community 9 - "FFmpeg Command Helpers"
Cohesion: 0.12
Nodes (10): _run_ffmpeg(), extract_audio(), unload_whisper_models(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command() (+2 more)

### Community 10 - "Test Stubs and Mocks"
Cohesion: 0.20
Nodes (18): RenderResult, command_exists(), app(), audio_only_file(), failing_client(), failing_renderer_client(), failing_selector_client(), failing_tracker_client() (+10 more)

### Community 11 - "Clip Selection Schemas"
Cohesion: 0.16
Nodes (19): LLMClip, LLMClipScores, LLMClipSelection, render_prompt(), TranscriptChunk, _payload(), _segment(), _settings() (+11 more)

### Community 12 - "Transcript Chunking"
Cohesion: 0.13
Nodes (16): TranscriptWord, build_candidate(), build_response_schema(), candidates_from_payload(), _clamp(), _clean_text(), _conciseness(), _finite_float() (+8 more)

### Community 13 - "Ollama Selection Client"
Cohesion: 0.14
Nodes (13): OllamaClipSelector, OllamaError, OllamaMalformedResponse, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama(), test_selector_returns_empty_when_every_chunk_is_malformed(), test_selector_skips_malformed_chunk_and_keeps_valid_one() (+5 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.10
Nodes (8): create_face_detector(), FaceDetectionError, FaceDetector, OpenCVYuNetDetector, OpenCVSpeakerTracker, test_missing_face_model_raises_actionable_error(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.14
Nodes (16): nextConfig, metadata, RootLayout(), viewport, NotFound(), AppShell(), NavItem, navItems (+8 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.15
Nodes (10): FaceBox, _association_score(), build_crop_plan(), summarize_choices(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres() (+2 more)

### Community 18 - "Transcript Segment Fitting"
Cohesion: 0.17
Nodes (12): _apply_progress(), _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), process_segmenter_job() (+4 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.18
Nodes (15): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, _face(), _frame(), test_exact_portrait_source_is_not_cropped() (+7 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 21 - "Clip API Endpoints"
Cohesion: 0.16
Nodes (6): api_error(), get_clip(), get_clip_file(), _get_clip_or_404(), sanitize_display_filename(), test_sanitize_display_filename()

### Community 22 - "Upload and File Utils"
Cohesion: 0.15
Nodes (6): create_job(), reject_oversized_upload(), human_size(), remove_tree(), job_upload_dir(), test_human_size()

### Community 23 - "Media Probe Service"
Cohesion: 0.21
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 24 - "Face Track State"
Cohesion: 0.18
Nodes (11): _centrality(), choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, FrameFaces, is_speech_active(), _median() (+3 more)

### Community 26 - "Upload Streaming Helpers"
Cohesion: 0.19
Nodes (9): EmptyUpload, file_extension(), stream_upload_to_path(), UploadTooLarge, test_file_extension_is_lowercase(), test_resolve_stored_path_rejects_traversal(), test_stream_upload_rejects_empty_and_removes_file(), test_stream_upload_rejects_oversized_and_removes_partial_file() (+1 more)

### Community 27 - "Landing Page UI"
Cohesion: 0.17
Nodes (16): AIClipperPage(), features, pipeline, ArrowRightIcon(), CpuIcon(), FileVideoIcon(), ShieldIcon(), FALLBACK_FORMATS (+8 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.22
Nodes (9): Job, JobState, claim_next_queued_job(), recover_interrupted_jobs(), _job(), test_claim_next_queued_job_marks_inspecting(), test_job_state_helpers(), test_progress_never_moves_backwards() (+1 more)

### Community 30 - "Database Setup"
Cohesion: 0.17
Nodes (6): _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), test_additive_migration_adds_phase4_clip_columns()

### Community 31 - "Job Cleanup and Tests"
Cohesion: 0.17
Nodes (11): delete_job_files(), _job_row(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_completed_job_removes_record_clips_and_media(), test_delete_job_files_refuses_non_uuid_ids(), test_delete_queued_job_removes_upload_without_worker(), test_delete_unknown_or_repeated_job_returns_404() (+3 more)

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.19
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 34 - "Transcript Processing"
Cohesion: 0.20
Nodes (5): Transcript, FasterWhisperTranscriber, _report(), _report_stage(), save_transcript()

### Community 35 - "Job API Operations"
Cohesion: 0.26
Nodes (5): delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips()

### Community 36 - "Segmenter UI Flow"
Cohesion: 0.25
Nodes (11): SegmenterPage(), ScissorsIcon(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady(), SegmenterForm(), handleDrop(), handleInputChange() (+3 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.37
Nodes (12): API_BASE_URL, ApiError, createSegmenterJob(), deleteJob(), errorFromResponse(), getHealth(), getJob(), getJobClips() (+4 more)

### Community 38 - "Transcript Schema Models"
Cohesion: 0.19
Nodes (5): TranscriptSegment, _fit_segment_range(), fits_hard(), fits_target(), _range_duration()

### Community 40 - "Crop Plan Schemas"
Cohesion: 0.20
Nodes (4): CropPlan, CropSample, interpolate_crop(), SpeakerTrackingError

### Community 42 - "Clip Selection Logic"
Cohesion: 0.20
Nodes (3): build_chunks(), ClipSelectionError, load_prompt_template()

### Community 44 - "API Shared Types"
Cohesion: 0.25
Nodes (7): Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`, `Frontend Next.js agent guidance`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 341 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `App Settings Paths` to `FFmpeg Clip Rendering`, `Config Validation Tests`, `Transcription Segments`, `Health API Checks`, `Clip Model Storage`, `Cancellation and Work`, `Worker Pipeline Services`, `FFmpeg Command Helpers`, `Test Stubs and Mocks`, `Clip Selection Schemas`, `Transcript Chunking`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `Transcript Segment Fitting`, `Face Tracking Frames`, `Speaker Tracking Results`, `Upload and File Utils`, `Media Probe Service`, `Face Track State`, `Service Config Modules`, `Upload Streaming Helpers`, `Database Setup`, `Job Cleanup and Tests`, `Clip Candidate Scoring`, `Transcript Processing`, `Transcript Schema Models`, `Ollama Client Probe`, `Frame Sampling`, `Tracker Orchestration Test`?**
  _High betweenness centrality (0.304) - this node is a cross-community bridge._
- **Are the 115 inferred relationships involving `Settings` (e.g. with `health()` and `create_job()`) actually correct?**
  _`Settings` has 115 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Ollama timeout behavior and tuning guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FFmpeg Clip Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.10042283298097252 - nodes in this community are weakly interconnected._
- **Why does `JobWorker` connect `Worker Pipeline Services` to `App Settings Paths`, `Health API Checks`, `Cancellation and Work`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `process_job()` (e.g. with `Settings` and `Job`) actually correct?**
  _`process_job()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `Config Validation Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.09268292682926829 - nodes in this community are weakly interconnected._