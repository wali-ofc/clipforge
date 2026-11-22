# Graph Report - clipforge  (2026-11-22)

## Corpus Check
- 88 files · ~62,082 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1314 nodes · 3841 edges · 80 communities (49 shown, 31 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 379 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e099c57`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rendering.py
- test_upload_jobs.py
- run_command
- test_transcript.py
- main.py
- pipeline.py
- create_app
- Frontend UI Components
- probe_media
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
- pathlib
- routes_sources.py
- FaceTrack
- CancelToken
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- models/job.py
- test_hardening.py
- Clip Candidate Scoring
- Project Docs Concepts
- Job API Operations
- SegmenterWorkspace
- Frontend API Client
- compact_selection.py
- speaker_tracking.py
- ollama.py
- Clip Selection Logic
- SegmenterWorkspace.tsx
- Design System: ClipForge
- main.py
- runner.py
- PostCSS Config
- Backend Package Meta
- conftest.py
- apply_progress
- config.py
- JobCancelled
- CompactOllamaClipSelector
- Product
- test_compact_selection.py
- test_sources.py
- score_candidate
- SelectionTimings
- SampledFrame

## God Nodes (most connected - your core abstractions)
1. `Settings` - 227 edges
2. `utc_now()` - 39 edges
3. `create_app()` - 37 edges
4. `process_job()` - 35 edges
5. `Transcript` - 35 edges
6. `generate_candidate_regions()` - 33 edges
7. `TranscriptSegment` - 33 edges
8. `probe_media()` - 33 edges
9. `JobStatusView()` - 33 edges
10. `Job` - 32 edges

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

## Communities (80 total, 31 thin omitted)

### Community 0 - "test_rendering.py"
Cohesion: 0.10
Nodes (22): MediaInfo, build_crop_commands_file(), FFmpegClipRenderer, format_sendcmd_path(), RenderingError, RenderResult, _verify_output(), _media_info() (+14 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.09
Nodes (30): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+22 more)

### Community 2 - "run_command"
Cohesion: 0.11
Nodes (11): sample_clip_frames(), extract_audio(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate() (+3 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.08
Nodes (26): SegmentGroup, build_transcript(), _clamp(), _finite_float(), is_non_speech_text(), _load_whisper_model(), _report(), _report_stage() (+18 more)

### Community 4 - "main.py"
Cohesion: 0.13
Nodes (12): health(), _configure_logging(), HealthCheck, HealthLimits, HealthResponse, check_face_detection(), check_media_tools(), check_ollama() (+4 more)

### Community 5 - "pipeline.py"
Cohesion: 0.13
Nodes (16): _apply_progress(), process_segmenter_job(), FasterWhisperTranscriber, job_clips_dir(), job_work_dir(), relative_to_data_dir(), resolve_stored_path(), utc_now() (+8 more)

### Community 6 - "create_app"
Cohesion: 0.13
Nodes (8): get_settings(), create_engine_from_settings(), create_session_factory(), init_db(), create_app(), lifespan(), reject_oversized_upload(), JobWorker

### Community 7 - "Frontend UI Components"
Cohesion: 0.14
Nodes (28): JobPage(), AlertIcon(), CheckIcon(), DownloadIcon(), FileVideoIcon(), SpinnerIcon(), XIcon(), badgeClasses() (+20 more)

### Community 8 - "probe_media"
Cohesion: 0.22
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 9 - "Settings"
Cohesion: 0.10
Nodes (6): Settings, cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), ensure_data_dirs()

### Community 10 - "test_clip_selection.py"
Cohesion: 0.19
Nodes (16): LLMClip, LLMClipScores, LLMClipSelection, build_chunks(), TranscriptChunk, _payload(), _segment(), test_boundaries_expand_across_segments() (+8 more)

### Community 11 - "generate_candidate_regions"
Cohesion: 0.09
Nodes (35): build_units(), flush(), _clamp(), _containment(), _describe(), _gap(), generate_candidate_regions(), distinct() (+27 more)

### Community 12 - "services/clip_selection.py"
Cohesion: 0.13
Nodes (14): TranscriptSegment, TranscriptWord, build_candidate(), _clamp(), _clean_text(), _fit_segment_range(), fits_hard(), fits_target() (+6 more)

### Community 13 - "Ollama Selection Client"
Cohesion: 0.11
Nodes (15): Transcript, OllamaClipSelector, _report(), OllamaError, OllamaMalformedResponse, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama() (+7 more)

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

### Community 18 - "segmenter.py"
Cohesion: 0.19
Nodes (11): _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), _render_range(), _run_ffmpeg() (+3 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.14
Nodes (18): assign_mouth_motion(), build_face_tracks(), build_speech_intervals(), compute_crop_geometry(), CropGeometry, FrameFace, FrameFaces, _face() (+10 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): FaceDetectionError, build_centered_result(), _extract_mouth_patch(), _load_frame(), OpenCVSpeakerTracker, _report(), SpeakerTrackingResult, _to_grayscale() (+3 more)

### Community 21 - "pathlib"
Cohesion: 0.10
Nodes (17): _check_upload_preconditions(), create_source(), create_job(), EmptyUpload, file_extension(), human_size(), remove_tree(), sanitize_display_filename() (+9 more)

### Community 23 - "routes_sources.py"
Cohesion: 0.12
Nodes (12): create_source_segment(), delete_source(), get_source(), _get_source_or_404(), _job_count(), list_source_jobs(), list_sources(), _source_read() (+4 more)

### Community 27 - "Landing Page UI"
Cohesion: 0.20
Nodes (15): NotFound(), AIClipperPage(), steps, ArrowRightIcon(), RegMarks(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady() (+7 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.14
Nodes (9): Job, JobKind, JobState, JobRead, _job(), test_claim_next_queued_job_marks_inspecting(), test_job_state_helpers(), test_progress_never_moves_backwards() (+1 more)

### Community 30 - "models/job.py"
Cohesion: 0.14
Nodes (4): _apply_sqlite_additive_migrations(), Base, ensure_sqlite_directory(), test_additive_migration_adds_phase4_clip_columns()

### Community 31 - "test_hardening.py"
Cohesion: 0.17
Nodes (15): client(), _clip_row(), _job_dirs(), _job_row(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_active_job_cancels_worker_and_removes_media(), test_delete_completed_job_removes_record_clips_and_media() (+7 more)

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.20
Nodes (11): candidates_from_payload(), ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie() (+3 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.17
Nodes (7): api_error(), delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips(), load_transcript()

### Community 36 - "SegmenterWorkspace"
Cohesion: 0.24
Nodes (12): SegmenterPage(), specimens, ScissorsIcon(), SegmenterWorkspace(), handleCreateSource(), handleCut(), handleDeleteSource(), handleDrop() (+4 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.31
Nodes (18): API_BASE_URL, ApiError, createSegmenterJob(), createSource(), createSourceSegment(), deleteJob(), deleteSource(), errorFromResponse() (+10 more)

### Community 39 - "compact_selection.py"
Cohesion: 0.11
Nodes (26): CompactClipProposal, CandidateRegion, build_compact_candidate(), candidates_from_compact_payload(), _clamp(), _clean_category(), _clean_hook(), find_region() (+18 more)

### Community 40 - "speaker_tracking.py"
Cohesion: 0.12
Nodes (15): _centered_plan(), choose_active_tracks(), _clamp(), _clamp_center(), CropPlan, CropSample, interpolate_crop(), is_speech_active() (+7 more)

### Community 41 - "ollama.py"
Cohesion: 0.09
Nodes (12): _count(), _model_is_available(), _normalize_model_name(), OllamaChatResult, OllamaChatStats, OllamaClient, OllamaProbe, _parse_chat_stats() (+4 more)

### Community 42 - "Clip Selection Logic"
Cohesion: 0.20
Nodes (5): ClipSelectionError, load_prompt_template(), render_prompt(), _settings(), test_prompt_placeholder_error_is_actionable()

### Community 44 - "SegmenterWorkspace.tsx"
Cohesion: 0.24
Nodes (9): FALLBACK_FORMATS, Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind (+1 more)

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "main.py"
Cohesion: 0.15
Nodes (6): get_session(), get_clip(), get_clip_file(), _get_clip_or_404(), Clip, ClipRead

### Community 48 - "runner.py"
Cohesion: 0.14
Nodes (5): ClipSelector, ClipRenderer, SpeakerTracker, Transcriber, recover_interrupted_jobs()

### Community 57 - "conftest.py"
Cohesion: 0.23
Nodes (17): command_exists(), app(), audio_only_file(), failing_client(), failing_renderer_client(), failing_selector_client(), failing_tracker_client(), _ffmpeg_command() (+9 more)

### Community 59 - "apply_progress"
Cohesion: 0.19
Nodes (8): apply_progress(), claim_next_queued_job(), _raise_if_cancelled(), _select_clips_with_progress(), on_progress(), _transcribe_with_progress(), on_progress(), on_stage()

### Community 63 - "CompactOllamaClipSelector"
Cohesion: 0.20
Nodes (15): CompactOllamaClipSelector, estimate_tokens(), FakeCompactClient, _selector_with_regions(), _speech(), test_empty_transcript_returns_no_candidates_and_skips_ollama(), factory(), test_selector_handles_malformed_ollama_response() (+7 more)

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 72 - "test_compact_selection.py"
Cohesion: 0.17
Nodes (10): create_clip_selector(), build_compact_schema(), load_compact_instructions(), render_compact_prompt(), _segment(), test_compact_prompt_puts_static_instructions_first(), test_compact_schema_contains_only_the_six_required_fields(), test_factory_keeps_legacy_selector_behind_config() (+2 more)

### Community 73 - "test_sources.py"
Cohesion: 0.33
Nodes (7): Source, _create_source(), _cut(), test_multiple_cuts_reuse_one_source_and_survive_job_deletion(), test_source_segment_validation(), test_source_upload_creates_project_without_a_job(), test_unknown_source_returns_404()

### Community 74 - "score_candidate"
Cohesion: 0.24
Nodes (6): build_response_schema(), _conciseness(), _finite_float(), _normalized_score(), score_candidate(), test_response_schema_requires_clip_fields()

### Community 76 - "SampledFrame"
Cohesion: 0.33
Nodes (3): SampledFrame, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 436 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_rendering.py`, `test_upload_jobs.py`, `run_command`, `test_transcript.py`, `main.py`, `pipeline.py`, `create_app`, `probe_media`, `test_clip_selection.py`, `generate_candidate_regions`, `services/clip_selection.py`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `segmenter.py`, `Face Tracking Frames`, `Speaker Tracking Results`, `pathlib`, `routes_sources.py`, `models/job.py`, `test_hardening.py`, `Clip Candidate Scoring`, `compact_selection.py`, `speaker_tracking.py`, `ollama.py`, `Clip Selection Logic`, `runner.py`, `conftest.py`, `apply_progress`, `config.py`, `CompactOllamaClipSelector`, `test_compact_selection.py`, `score_candidate`, `SelectionTimings`, `SampledFrame`?**
  _High betweenness centrality (0.284) - this node is a cross-community bridge._
- **Are the 146 inferred relationships involving `Settings` (e.g. with `health()` and `generate_candidate_regions()`) actually correct?**
  _`Settings` has 146 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_rendering.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09936575052854123 - nodes in this community are weakly interconnected._
- **Why does `Transcript` connect `Ollama Selection Client` to `Job API Operations`, `test_transcript.py`, `pipeline.py`, `compact_selection.py`, `speaker_tracking.py`, `test_compact_selection.py`, `test_clip_selection.py`, `services/clip_selection.py`, `runner.py`, `Speaker Tracking Results`, `apply_progress`, `CompactOllamaClipSelector`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `process_job()` (e.g. with `Settings` and `ClipSelectionError`) actually correct?**
  _`process_job()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08748615725359911 - nodes in this community are weakly interconnected._