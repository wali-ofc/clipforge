# Graph Report - clipforge  (2026-11-22)

## Corpus Check
- 89 files · ~62,730 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1331 nodes · 3912 edges · 78 communities (49 shown, 29 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 435 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e9843d6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rendering.py
- test_upload_jobs.py
- run_command
- test_transcript.py
- main.py
- pipeline.py
- OllamaClient
- Frontend UI Components
- test_upload_jobs.py
- Settings
- test_clip_selection.py
- generate_candidate_regions
- services/clip_selection.py
- Ollama Selection Client
- Face Detection Core
- Frontend Dependencies
- App Shell Layout
- Crop Plan Geometry
- segmenter.py
- Face Tracking Frames
- Speaker Tracking Results
- routes_sources.py
- speaker_tracking.py
- lifespan
- Landing Page UI
- Frontend TypeScript Config
- create_engine_from_settings
- config.py
- bench_selection.py
- Clip Candidate Scoring
- Project Docs Concepts
- Job API Operations
- SegmenterWorkspace
- Frontend API Client
- compact_selection.py
- interpolate_crop
- ollama.py
- Clip Selection Logic
- SegmenterWorkspace.tsx
- Design System: ClipForge
- routes_upload.py
- routes_health.py
- PostCSS Config
- Backend Package Meta
- test_sources.py
- get_clip_file
- test_hardening.py
- CompactOllamaClipSelector
- Product
- build_compact_schema
- face_detection.py

## God Nodes (most connected - your core abstractions)
1. `Settings` - 235 edges
2. `Job` - 46 edges
3. `utc_now()` - 39 edges
4. `create_app()` - 37 edges
5. `JobState` - 37 edges
6. `process_job()` - 37 edges
7. `Transcript` - 36 edges
8. `generate_candidate_regions()` - 35 edges
9. `JobStatusView()` - 33 edges
10. `TranscriptSegment` - 33 edges

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
- 2-file cycle: `backend/app/db.py -> backend/app/models/source.py -> backend/app/db.py`

## Communities (78 total, 29 thin omitted)

### Community 0 - "test_rendering.py"
Cohesion: 0.07
Nodes (32): _extract_rotation(), MediaInfo, MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), build_crop_commands_file(), _even() (+24 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.07
Nodes (34): _check_upload_preconditions(), create_source(), create_job(), reject_oversized_upload(), EmptyUpload, file_extension(), human_size(), remove_tree() (+26 more)

### Community 2 - "run_command"
Cohesion: 0.11
Nodes (9): unload_whisper_models(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate(), test_run_command_stops_promptly_when_cancelled() (+1 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.07
Nodes (29): Transcript, SegmentGroup, build_transcript(), _clamp(), extract_audio(), FasterWhisperTranscriber, _finite_float(), is_non_speech_text() (+21 more)

### Community 4 - "main.py"
Cohesion: 0.17
Nodes (9): get_settings(), create_app(), check_media_tools(), check_ollama(), _check_tool(), check_whisper(), media_tools_available(), ToolCheck (+1 more)

### Community 5 - "pipeline.py"
Cohesion: 0.07
Nodes (31): Job, JobState, ClipSelector, ClipRenderer, SpeakerTracker, Transcriber, CancelToken, job_work_dir() (+23 more)

### Community 6 - "OllamaClient"
Cohesion: 0.16
Nodes (5): OllamaClient, OllamaProbe, test_chat_json_result_parses_server_timings(), test_chat_json_still_returns_only_the_payload(), handler()

### Community 7 - "Frontend UI Components"
Cohesion: 0.16
Nodes (22): JobPage(), DownloadIcon(), FileVideoIcon(), badgeClasses(), ClipCard(), Detail(), fallbackNote(), JobStatusView() (+14 more)

### Community 8 - "test_upload_jobs.py"
Cohesion: 0.14
Nodes (13): test_clip_file_requires_completed_render(), test_clip_list_is_empty_in_phase_one(), test_job_record_survives_app_restart(), test_long_video_produces_candidate_clips(), test_rendering_failure_marks_clip_failed(), test_tracking_failure_keeps_job_and_centres_crop(), test_upload_rejects_file_without_video_stream(), test_valid_upload_creates_queued_job_and_worker_completes() (+5 more)

### Community 9 - "Settings"
Cohesion: 0.07
Nodes (32): Settings, cleanup_orphan_job_dirs(), job_directories(), _safe_child(), RenderResult, ensure_data_dirs(), command_exists(), app() (+24 more)

### Community 10 - "test_clip_selection.py"
Cohesion: 0.15
Nodes (18): LLMClip, LLMClipScores, LLMClipSelection, build_chunks(), candidates_from_payload(), TranscriptChunk, _payload(), _segment() (+10 more)

### Community 11 - "generate_candidate_regions"
Cohesion: 0.07
Nodes (37): TranscriptSegment, build_units(), flush(), _clamp(), _containment(), _describe(), _gap(), generate_candidate_regions() (+29 more)

### Community 12 - "services/clip_selection.py"
Cohesion: 0.13
Nodes (18): TranscriptWord, build_candidate(), build_response_schema(), _clamp(), _conciseness(), _finite_float(), _fit_segment_range(), fits_hard() (+10 more)

### Community 13 - "Ollama Selection Client"
Cohesion: 0.22
Nodes (11): OllamaClipSelector, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama(), test_selector_returns_empty_when_every_chunk_is_malformed(), test_selector_skips_malformed_chunk_and_keeps_valid_one(), test_selector_skips_no_speech_without_calling_ollama(), factory() (+3 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.13
Nodes (4): create_face_detector(), FaceDetector, OpenCVYuNetDetector, test_missing_face_model_raises_actionable_error()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.11
Nodes (22): react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6, @types/react@19.3.0, @types/react-dom@19.3.0, typescript@5.9.3 (+14 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.09
Nodes (22): nextConfig, dependencies, next@16.4.5, react@19.3.1, archivo, metadata, robotoMono, RootLayout() (+14 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.12
Nodes (12): FaceBox, _association_score(), build_crop_plan(), _centrality(), summarize_choices(), TrackChoice, _FakeDetector, test_crop_plan_interpolates_between_samples() (+4 more)

### Community 18 - "segmenter.py"
Cohesion: 0.16
Nodes (13): _apply_progress(), _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), process_segmenter_job() (+5 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.18
Nodes (15): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, _face(), _frame(), test_exact_portrait_source_is_not_cropped() (+7 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 23 - "routes_sources.py"
Cohesion: 0.25
Nodes (10): create_source_segment(), delete_source(), get_source(), _get_source_or_404(), _job_count(), list_source_jobs(), list_sources(), _source_read() (+2 more)

### Community 24 - "speaker_tracking.py"
Cohesion: 0.20
Nodes (10): choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, FrameFaces, is_speech_active(), _median(), _track_stats() (+2 more)

### Community 25 - "lifespan"
Cohesion: 0.16
Nodes (3): _configure_logging(), lifespan(), JobWorker

### Community 27 - "Landing Page UI"
Cohesion: 0.16
Nodes (21): NotFound(), AIClipperPage(), steps, AlertIcon(), ArrowRightIcon(), CheckIcon(), RegMarks(), SpinnerIcon() (+13 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "create_engine_from_settings"
Cohesion: 0.16
Nodes (6): _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), test_additive_migration_adds_phase4_clip_columns()

### Community 30 - "config.py"
Cohesion: 0.13
Nodes (4): Base, Clip, delete_source_files(), is_job_uuid()

### Community 31 - "bench_selection.py"
Cohesion: 0.20
Nodes (4): estimate_tokens(), build_settings(), main(), TrackingClient

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.19
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.26
Nodes (5): delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips()

### Community 36 - "SegmenterWorkspace"
Cohesion: 0.24
Nodes (12): SegmenterPage(), specimens, ScissorsIcon(), SegmenterWorkspace(), handleCreateSource(), handleCut(), handleDeleteSource(), handleDrop() (+4 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.31
Nodes (18): API_BASE_URL, ApiError, createSegmenterJob(), createSource(), createSourceSegment(), deleteJob(), deleteSource(), errorFromResponse() (+10 more)

### Community 39 - "compact_selection.py"
Cohesion: 0.13
Nodes (28): CompactClipProposal, CandidateRegion, build_compact_candidate(), candidates_from_compact_payload(), _clamp(), _clean_category(), _clean_hook(), find_region() (+20 more)

### Community 40 - "interpolate_crop"
Cohesion: 0.20
Nodes (4): CropPlan, CropSample, interpolate_crop(), SpeakerTrackingError

### Community 41 - "ollama.py"
Cohesion: 0.16
Nodes (7): _count(), _model_is_available(), _normalize_model_name(), OllamaChatResult, OllamaChatStats, _parse_chat_stats(), _seconds()

### Community 42 - "Clip Selection Logic"
Cohesion: 0.18
Nodes (6): _clean_text(), ClipSelectionError, load_prompt_template(), render_prompt(), _settings(), test_prompt_placeholder_error_is_actionable()

### Community 44 - "SegmenterWorkspace.tsx"
Cohesion: 0.24
Nodes (9): FALLBACK_FORMATS, Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind (+1 more)

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "routes_upload.py"
Cohesion: 0.08
Nodes (9): get_session(), api_error(), JobKind, ClipRead, JobRead, job_clips_dir(), job_upload_dir(), relative_to_data_dir() (+1 more)

### Community 48 - "routes_health.py"
Cohesion: 0.30
Nodes (5): health(), HealthCheck, HealthLimits, HealthResponse, check_face_detection()

### Community 57 - "test_sources.py"
Cohesion: 0.33
Nodes (6): _create_source(), _cut(), test_multiple_cuts_reuse_one_source_and_survive_job_deletion(), test_source_segment_validation(), test_source_upload_creates_project_without_a_job(), test_unknown_source_returns_404()

### Community 58 - "get_clip_file"
Cohesion: 0.36
Nodes (3): get_clip(), get_clip_file(), _get_clip_or_404()

### Community 62 - "test_hardening.py"
Cohesion: 0.11
Nodes (10): delete_job_files(), JobCancelled, utc_now(), BlockingTranscriber, _clip_row(), _job_row(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_job_files_refuses_non_uuid_ids() (+2 more)

### Community 63 - "CompactOllamaClipSelector"
Cohesion: 0.11
Nodes (22): create_clip_selector(), CompactOllamaClipSelector, load_compact_instructions(), OllamaError, OllamaMalformedResponse, FakeCompactClient, _segment(), _selector_with_regions() (+14 more)

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 75 - "build_compact_schema"
Cohesion: 0.20
Nodes (4): build_compact_schema(), log_selection_timings(), SelectionTimings, test_compact_schema_contains_only_the_six_required_fields()

### Community 76 - "face_detection.py"
Cohesion: 0.15
Nodes (7): FaceDetectionError, sample_clip_frames(), SampledFrame, OpenCVSpeakerTracker, test_tracker_orchestration_builds_a_crop_plan(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 440 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_rendering.py`, `test_upload_jobs.py`, `run_command`, `test_transcript.py`, `main.py`, `pipeline.py`, `OllamaClient`, `test_upload_jobs.py`, `test_clip_selection.py`, `generate_candidate_regions`, `services/clip_selection.py`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `segmenter.py`, `Face Tracking Frames`, `Speaker Tracking Results`, `routes_sources.py`, `speaker_tracking.py`, `lifespan`, `create_engine_from_settings`, `config.py`, `bench_selection.py`, `Clip Candidate Scoring`, `compact_selection.py`, `ollama.py`, `Clip Selection Logic`, `routes_upload.py`, `routes_health.py`, `test_hardening.py`, `CompactOllamaClipSelector`, `build_compact_schema`, `face_detection.py`?**
  _High betweenness centrality (0.313) - this node is a cross-community bridge._
- **Are the 159 inferred relationships involving `Settings` (e.g. with `health()` and `_check_upload_preconditions()`) actually correct?**
  _`Settings` has 159 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_rendering.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07086197778952935 - nodes in this community are weakly interconnected._
- **Why does `FaceBox` connect `Crop Plan Geometry` to `Settings`, `face_detection.py`, `Face Detection Core`, `Face Tracking Frames`, `Speaker Tracking Results`, `speaker_tracking.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Job` (e.g. with `delete_job()` and `get_job()`) actually correct?**
  _`Job` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07005649717514124 - nodes in this community are weakly interconnected._