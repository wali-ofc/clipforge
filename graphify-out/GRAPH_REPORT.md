# Graph Report - clipforge  (2026-11-23)

## Corpus Check
- 92 files · ~70,420 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1464 nodes · 4435 edges · 79 communities (43 shown, 36 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 454 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e9ed90f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rendering.py
- routes_sources.py
- Job
- test_transcript.py
- main.py
- pipeline.py
- conftest.py
- Frontend UI Components
- test_upload_jobs.py
- Settings
- services/clip_selection.py
- generate_candidate_regions
- run_command
- routes_health.py
- Face Detection Core
- Frontend Dependencies
- App Shell Layout
- Crop Plan Geometry
- segmenter.py
- Face Tracking Frames
- Speaker Tracking Results
- config.py
- FaceTrack
- Landing Page UI
- Frontend TypeScript Config
- JobWorker
- cleanup_orphan_job_dirs
- bench_selection.py
- Project Docs Concepts
- api_error
- SegmenterWorkspace
- Frontend API Client
- compact_selection.py
- speaker_tracking.py
- config.py
- SegmenterWorkspace.tsx
- Design System: ClipForge
- routes_jobs.py
- JobCancelled
- PostCSS Config
- Backend Package Meta
- probe_media
- test_hardening.py
- CompactOllamaClipSelector
- Product
- OllamaClient
- test_captions.py
- build_compact_schema
- SampledFrame
- CancelToken
- JobKind

## God Nodes (most connected - your core abstractions)
1. `Settings` - 233 edges
2. `Job` - 54 edges
3. `Transcript` - 52 edges
4. `JobStatusView()` - 41 edges
5. `utc_now()` - 41 edges
6. `SegmenterWorkspace()` - 39 edges
7. `TranscriptSegment` - 38 edges
8. `create_app()` - 37 edges
9. `JobState` - 37 edges
10. `process_job()` - 37 edges

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

## Communities (79 total, 36 thin omitted)

### Community 0 - "test_rendering.py"
Cohesion: 0.11
Nodes (22): MediaInfo, build_crop_commands_file(), FFmpegClipRenderer, format_sendcmd_path(), RenderingError, _verify_output(), _media_info(), _require_ffmpeg() (+14 more)

### Community 1 - "routes_sources.py"
Cohesion: 0.05
Nodes (44): get_session(), api_error(), _cue_payload(), get_clip(), get_clip_captions(), get_clip_file(), _get_clip_or_404(), _resolve_transcript_for_clip() (+36 more)

### Community 2 - "Job"
Cohesion: 0.13
Nodes (12): delete_source(), Job, JobState, utc_now(), apply_progress(), claim_next_queued_job(), recover_interrupted_jobs(), _job() (+4 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.07
Nodes (30): _load_transcript_path(), Transcript, TranscriptWord, build_transcript(), _clamp(), FasterWhisperTranscriber, _finite_float(), is_non_speech_text() (+22 more)

### Community 4 - "main.py"
Cohesion: 0.12
Nodes (16): get_settings(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), _configure_logging(), create_app(), lifespan() (+8 more)

### Community 5 - "pipeline.py"
Cohesion: 0.09
Nodes (20): _run_source_transcription(), ClipSelector, ClipRenderer, _apply_progress(), process_segmenter_job(), SpeakerTracker, Transcriber, job_clips_dir() (+12 more)

### Community 6 - "conftest.py"
Cohesion: 0.18
Nodes (19): RenderResult, command_exists(), app(), audio_only_file(), client(), failing_client(), failing_renderer_client(), failing_selector_client() (+11 more)

### Community 7 - "Frontend UI Components"
Cohesion: 0.12
Nodes (34): JobPage(), AlertIcon(), CheckIcon(), CopyIcon(), DownloadIcon(), FileVideoIcon(), SpinnerIcon(), XIcon() (+26 more)

### Community 8 - "test_upload_jobs.py"
Cohesion: 0.09
Nodes (30): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+22 more)

### Community 10 - "services/clip_selection.py"
Cohesion: 0.05
Nodes (61): LLMClip, LLMClipScores, LLMClipSelection, build_candidate(), build_chunks(), build_response_schema(), candidates_from_payload(), _clamp() (+53 more)

### Community 11 - "generate_candidate_regions"
Cohesion: 0.08
Nodes (37): TranscriptSegment, build_units(), flush(), _clamp(), _containment(), _describe(), _gap(), generate_candidate_regions() (+29 more)

### Community 12 - "run_command"
Cohesion: 0.12
Nodes (9): sample_clip_frames(), extract_audio(), CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate() (+1 more)

### Community 13 - "routes_health.py"
Cohesion: 0.38
Nodes (4): health(), HealthCheck, HealthLimits, HealthResponse

### Community 14 - "Face Detection Core"
Cohesion: 0.13
Nodes (4): create_face_detector(), FaceDetector, OpenCVYuNetDetector, test_missing_face_model_raises_actionable_error()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.10
Nodes (18): nextConfig, archivo, metadata, robotoMono, RootLayout(), viewport, AppShell(), NavItem (+10 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.17
Nodes (9): FaceBox, _association_score(), build_crop_plan(), _centrality(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres() (+1 more)

### Community 18 - "segmenter.py"
Cohesion: 0.17
Nodes (12): _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), _render_range(), _run_ffmpeg() (+4 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.14
Nodes (18): assign_mouth_motion(), build_face_tracks(), build_speech_intervals(), compute_crop_geometry(), CropGeometry, FrameFace, FrameFaces, _face() (+10 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): FaceDetectionError, build_centered_result(), _extract_mouth_patch(), _load_frame(), OpenCVSpeakerTracker, _report(), SpeakerTrackingResult, _to_grayscale() (+3 more)

### Community 27 - "Landing Page UI"
Cohesion: 0.18
Nodes (16): NotFound(), AIClipperPage(), steps, ArrowRightIcon(), RegMarks(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady() (+8 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 30 - "cleanup_orphan_job_dirs"
Cohesion: 0.18
Nodes (6): cleanup_orphan_job_dirs(), is_job_uuid(), job_directories(), _safe_child(), ensure_data_dirs(), _job_dirs()

### Community 31 - "bench_selection.py"
Cohesion: 0.17
Nodes (4): estimate_tokens(), build_settings(), main(), TrackingClient

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "api_error"
Cohesion: 0.20
Nodes (13): _caption_filename(), _cue_payload(), delete_job(), download_job_captions_srt(), download_job_captions_txt(), get_job(), get_job_caption_range(), get_job_captions() (+5 more)

### Community 36 - "SegmenterWorkspace"
Cohesion: 0.18
Nodes (16): SegmenterPage(), specimens, ScissorsIcon(), copyToClipboard(), cueText(), rangeCaptionText(), SegmenterWorkspace(), handleCopyCaptionText() (+8 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.21
Nodes (24): handleGenerateTranscript(), handleGenerateTranscript(), API_BASE_URL, ApiError, createSegmenterJob(), createSource(), createSourceSegment(), deleteJob() (+16 more)

### Community 39 - "compact_selection.py"
Cohesion: 0.11
Nodes (31): CompactClipProposal, CandidateRegion, create_clip_selector(), build_compact_candidate(), candidates_from_compact_payload(), _clamp(), _clean_category(), _clean_hook() (+23 more)

### Community 40 - "speaker_tracking.py"
Cohesion: 0.12
Nodes (15): _centered_plan(), choose_active_tracks(), _clamp(), _clamp_center(), CropPlan, CropSample, interpolate_crop(), is_speech_active() (+7 more)

### Community 41 - "config.py"
Cohesion: 0.14
Nodes (8): _count(), _model_is_available(), _normalize_model_name(), OllamaChatResult, OllamaChatStats, OllamaProbe, _parse_chat_stats(), _seconds()

### Community 44 - "SegmenterWorkspace.tsx"
Cohesion: 0.14
Nodes (16): CaptionPreview, FALLBACK_FORMATS, ParsedRange, parseRanges(), parseTimestamp(), loadCaptionPreview(), CaptionCue, CaptionDefaults (+8 more)

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "routes_jobs.py"
Cohesion: 0.12
Nodes (10): _apply_sqlite_additive_migrations(), Base, Source, test_additive_migration_adds_phase4_clip_columns(), _create_source(), _cut(), test_multiple_cuts_reuse_one_source_and_survive_job_deletion(), test_source_segment_validation() (+2 more)

### Community 58 - "probe_media"
Cohesion: 0.23
Nodes (9): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file(), test_probe_rejects_corrupt_file() (+1 more)

### Community 62 - "test_hardening.py"
Cohesion: 0.16
Nodes (15): Clip, delete_job_files(), _clip_row(), _job_row(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_active_job_cancels_worker_and_removes_media(), test_delete_completed_job_removes_record_clips_and_media() (+7 more)

### Community 63 - "CompactOllamaClipSelector"
Cohesion: 0.11
Nodes (20): ClipSelectionError, CompactOllamaClipSelector, load_compact_instructions(), OllamaError, OllamaMalformedResponse, FakeCompactClient, _segment(), _selector_with_regions() (+12 more)

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 69 - "OllamaClient"
Cohesion: 0.18
Nodes (4): OllamaClient, test_chat_json_result_parses_server_timings(), test_chat_json_still_returns_only_the_payload(), handler()

### Community 71 - "test_captions.py"
Cohesion: 0.07
Nodes (58): _apply_romanization(), CaptionCue, captions_for_range(), captions_for_transcript(), captions_to_plain_text(), CaptionWord, _clamp(), _clean_cue_text() (+50 more)

### Community 75 - "build_compact_schema"
Cohesion: 0.20
Nodes (4): build_compact_schema(), log_selection_timings(), SelectionTimings, test_compact_schema_contains_only_the_six_required_fields()

### Community 76 - "SampledFrame"
Cohesion: 0.33
Nodes (3): SampledFrame, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

### Community 77 - "CancelToken"
Cohesion: 0.11
Nodes (8): CancelToken, _raise_if_cancelled(), _select_clips_with_progress(), on_progress(), on_progress(), on_stage(), test_process_job_marks_preexisting_cancellation(), test_run_command_stops_promptly_when_cancelled()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 459 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_rendering.py`, `routes_sources.py`, `Job`, `test_transcript.py`, `main.py`, `pipeline.py`, `conftest.py`, `test_upload_jobs.py`, `services/clip_selection.py`, `generate_candidate_regions`, `run_command`, `routes_health.py`, `Face Detection Core`, `Crop Plan Geometry`, `segmenter.py`, `Face Tracking Frames`, `Speaker Tracking Results`, `config.py`, `JobWorker`, `cleanup_orphan_job_dirs`, `bench_selection.py`, `compact_selection.py`, `speaker_tracking.py`, `config.py`, `routes_jobs.py`, `probe_media`, `test_hardening.py`, `CompactOllamaClipSelector`, `OllamaClient`, `build_compact_schema`, `SampledFrame`, `CancelToken`?**
  _High betweenness centrality (0.296) - this node is a cross-community bridge._
- **Are the 153 inferred relationships involving `Settings` (e.g. with `health()` and `cleanup_orphan_job_dirs()`) actually correct?**
  _`Settings` has 153 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_rendering.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1091753774680604 - nodes in this community are weakly interconnected._
- **Why does `Transcript` connect `test_transcript.py` to `routes_sources.py`, `api_error`, `pipeline.py`, `compact_selection.py`, `test_captions.py`, `speaker_tracking.py`, `services/clip_selection.py`, `CancelToken`, `Speaker Tracking Results`, `bench_selection.py`, `CompactOllamaClipSelector`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `Job` (e.g. with `_resolve_transcript_for_clip()` and `_caption_filename()`) actually correct?**
  _`Job` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Should `routes_sources.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05157232704402516 - nodes in this community are weakly interconnected._