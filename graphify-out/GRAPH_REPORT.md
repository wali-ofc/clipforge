# Graph Report - clipforge  (2026-11-22)

## Corpus Check
- 89 files · ~62,730 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1331 nodes · 3877 edges · 80 communities (48 shown, 32 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 326 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e099c57`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- rendering.py
- test_upload_jobs.py
- run_command
- test_transcript.py
- main.py
- pipeline.py
- OllamaClient
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
- schemas/job.py
- routes_sources.py
- speaker_tracking.py
- compact_selection.py
- Landing Page UI
- Frontend TypeScript Config
- Job and Clip Models
- models/job.py
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
- main.py
- candidates_from_payload
- PostCSS Config
- Backend Package Meta
- _fit_segment_range
- .render_clip
- transcription.py
- CompactOllamaClipSelector
- Product
- build_compact_schema
- SampledFrame

## God Nodes (most connected - your core abstractions)
1. `Settings` - 230 edges
2. `utc_now()` - 39 edges
3. `create_app()` - 37 edges
4. `Transcript` - 36 edges
5. `generate_candidate_regions()` - 35 edges
6. `process_job()` - 35 edges
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

## Communities (80 total, 32 thin omitted)

### Community 0 - "rendering.py"
Cohesion: 0.18
Nodes (13): MediaInfo, build_crop_commands_file(), RenderingError, _verify_output(), _media_info(), test_build_crop_commands_centers_without_plan(), test_build_crop_commands_clamps_and_dedupes(), test_build_crop_commands_file() (+5 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.05
Nodes (44): reject_oversized_upload(), EmptyUpload, file_extension(), human_size(), sanitize_display_filename(), stream_upload_to_path(), UploadTooLarge, test_clip_duration_range_is_validated() (+36 more)

### Community 2 - "run_command"
Cohesion: 0.12
Nodes (10): extract_audio(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate(), test_run_command_stops_promptly_when_cancelled() (+2 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.11
Nodes (20): SegmentGroup, build_transcript(), _clamp(), _finite_float(), is_non_speech_text(), _sanitize_segment(), _sanitize_word(), _FakeModel (+12 more)

### Community 4 - "main.py"
Cohesion: 0.06
Nodes (20): health(), _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), _configure_logging(), lifespan() (+12 more)

### Community 5 - "pipeline.py"
Cohesion: 0.07
Nodes (25): ClipSelector, ClipRenderer, _apply_progress(), process_segmenter_job(), SpeakerTracker, Transcriber, CancelToken, job_clips_dir() (+17 more)

### Community 6 - "OllamaClient"
Cohesion: 0.14
Nodes (5): OllamaClient, OllamaProbe, test_chat_json_result_parses_server_timings(), test_chat_json_still_returns_only_the_payload(), handler()

### Community 7 - "Frontend UI Components"
Cohesion: 0.14
Nodes (28): JobPage(), AlertIcon(), CheckIcon(), DownloadIcon(), FileVideoIcon(), SpinnerIcon(), XIcon(), badgeClasses() (+20 more)

### Community 8 - "probe_media"
Cohesion: 0.22
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 9 - "Settings"
Cohesion: 0.05
Nodes (40): get_settings(), Settings, create_app(), cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), RenderResult (+32 more)

### Community 10 - "test_clip_selection.py"
Cohesion: 0.20
Nodes (16): LLMClip, LLMClipScores, LLMClipSelection, TranscriptChunk, _payload(), _segment(), test_boundaries_expand_across_segments(), test_boundaries_snap_to_whole_segments() (+8 more)

### Community 11 - "generate_candidate_regions"
Cohesion: 0.08
Nodes (33): TranscriptSegment, build_units(), flush(), _clamp(), _describe(), _gap(), generate_candidate_regions(), _is_number_token() (+25 more)

### Community 12 - "services/clip_selection.py"
Cohesion: 0.15
Nodes (14): TranscriptWord, build_candidate(), build_response_schema(), _clamp(), _conciseness(), _finite_float(), _normalized_score(), _report() (+6 more)

### Community 13 - "Ollama Selection Client"
Cohesion: 0.16
Nodes (13): OllamaClipSelector, OllamaError, OllamaMalformedResponse, FakeOllamaClient, test_selector_reports_model_missing(), test_selector_reports_unavailable_ollama(), test_selector_returns_empty_when_every_chunk_is_malformed(), test_selector_skips_malformed_chunk_and_keeps_valid_one() (+5 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.08
Nodes (8): create_face_detector(), FaceDetectionError, FaceDetector, OpenCVYuNetDetector, sample_clip_frames(), test_missing_face_model_raises_actionable_error(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.09
Nodes (19): nextConfig, archivo, metadata, robotoMono, RootLayout(), viewport, AppShell(), NavItem (+11 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.15
Nodes (10): FaceBox, _association_score(), build_crop_plan(), summarize_choices(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres() (+2 more)

### Community 18 - "segmenter.py"
Cohesion: 0.18
Nodes (11): _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), _render_range(), _run_ffmpeg() (+3 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.18
Nodes (15): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, _face(), _frame(), test_exact_portrait_source_is_not_cropped() (+7 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 23 - "routes_sources.py"
Cohesion: 0.10
Nodes (16): _check_upload_preconditions(), create_source(), create_source_segment(), delete_source(), get_source(), _get_source_or_404(), _job_count(), list_source_jobs() (+8 more)

### Community 24 - "speaker_tracking.py"
Cohesion: 0.19
Nodes (11): _centrality(), choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, FrameFaces, is_speech_active(), _median() (+3 more)

### Community 25 - "compact_selection.py"
Cohesion: 0.21
Nodes (11): CandidateRegion, _containment(), distinct(), _iou(), _overlap(), build_compact_candidate(), _clamp(), _clean_category() (+3 more)

### Community 27 - "Landing Page UI"
Cohesion: 0.20
Nodes (15): NotFound(), AIClipperPage(), steps, ArrowRightIcon(), RegMarks(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady() (+7 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.16
Nodes (14): Job, JobState, utc_now(), claim_next_queued_job(), recover_interrupted_jobs(), _clip_row(), _job_row(), test_clip_file_endpoint_rejects_unsafe_stored_path() (+6 more)

### Community 30 - "models/job.py"
Cohesion: 0.14
Nodes (8): Base, Source, _create_source(), _cut(), test_multiple_cuts_reuse_one_source_and_survive_job_deletion(), test_source_segment_validation(), test_source_upload_creates_project_without_a_job(), test_unknown_source_returns_404()

### Community 31 - "bench_selection.py"
Cohesion: 0.20
Nodes (4): estimate_tokens(), build_settings(), main(), TrackingClient

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.25
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.14
Nodes (8): delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips(), Transcript, delete_job_files(), load_transcript()

### Community 36 - "SegmenterWorkspace"
Cohesion: 0.24
Nodes (12): SegmenterPage(), specimens, ScissorsIcon(), SegmenterWorkspace(), handleCreateSource(), handleCut(), handleDeleteSource(), handleDrop() (+4 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.31
Nodes (18): API_BASE_URL, ApiError, createSegmenterJob(), createSource(), createSourceSegment(), deleteJob(), deleteSource(), errorFromResponse() (+10 more)

### Community 39 - "compact_selection.py"
Cohesion: 0.15
Nodes (21): CompactClipProposal, candidates_from_compact_payload(), find_region(), _intersection(), refine_within_region(), render_compact_prompt(), _clip(), _region() (+13 more)

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

### Community 46 - "main.py"
Cohesion: 0.12
Nodes (8): get_session(), api_error(), get_clip(), get_clip_file(), _get_clip_or_404(), Clip, ClipRead, resolve_stored_path()

### Community 57 - "_fit_segment_range"
Cohesion: 0.60
Nodes (4): _fit_segment_range(), fits_hard(), fits_target(), _range_duration()

### Community 60 - ".render_clip"
Cohesion: 0.16
Nodes (9): _even(), FFmpegClipRenderer, format_sendcmd_path(), _require_ffmpeg(), test_dynamic_crop_follows_plan(), test_ffmpeg_clip_renderer_integration(), test_ffmpeg_clip_renderer_without_audio(), test_format_sendcmd_path() (+1 more)

### Community 62 - "transcription.py"
Cohesion: 0.13
Nodes (6): FasterWhisperTranscriber, _load_whisper_model(), _report(), _report_stage(), unload_whisper_models(), JobCancelled

### Community 63 - "CompactOllamaClipSelector"
Cohesion: 0.13
Nodes (20): create_clip_selector(), CompactOllamaClipSelector, load_compact_instructions(), FakeCompactClient, _segment(), _selector_with_regions(), _speech(), test_empty_transcript_returns_no_candidates_and_skips_ollama() (+12 more)

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 75 - "build_compact_schema"
Cohesion: 0.22
Nodes (4): build_compact_schema(), log_selection_timings(), SelectionTimings, test_compact_schema_contains_only_the_six_required_fields()

### Community 76 - "SampledFrame"
Cohesion: 0.25
Nodes (4): SampledFrame, OpenCVSpeakerTracker, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 439 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `rendering.py`, `test_upload_jobs.py`, `run_command`, `test_transcript.py`, `main.py`, `pipeline.py`, `OllamaClient`, `probe_media`, `test_clip_selection.py`, `generate_candidate_regions`, `services/clip_selection.py`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `segmenter.py`, `Face Tracking Frames`, `Speaker Tracking Results`, `routes_sources.py`, `speaker_tracking.py`, `compact_selection.py`, `Job and Clip Models`, `models/job.py`, `bench_selection.py`, `Clip Candidate Scoring`, `Job API Operations`, `compact_selection.py`, `ollama.py`, `Clip Selection Logic`, `main.py`, `candidates_from_payload`, `_fit_segment_range`, `.render_clip`, `transcription.py`, `CompactOllamaClipSelector`, `build_compact_schema`, `SampledFrame`?**
  _High betweenness centrality (0.284) - this node is a cross-community bridge._
- **Are the 104 inferred relationships involving `Settings` (e.g. with `health()` and `build_candidate()`) actually correct?**
  _`Settings` has 104 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05087719298245614 - nodes in this community are weakly interconnected._
- **Why does `FaceBox` connect `Crop Plan Geometry` to `Settings`, `SampledFrame`, `Face Detection Core`, `Face Tracking Frames`, `Speaker Tracking Results`, `speaker_tracking.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Transcript` (e.g. with `OpenCVSpeakerTracker` and `SpeakerTracker`) actually correct?**
  _`Transcript` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `run_command` be split into smaller, more focused modules?**
  _Cohesion score 0.12433862433862433 - nodes in this community are weakly interconnected._