# Graph Report - clipforge  (2026-11-23)

## Corpus Check
- 92 files · ~70,368 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: .example 2, (none) 2, .log 2)

## Summary
- 1462 nodes · 4428 edges · 75 communities (44 shown, 31 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 454 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d77e76a9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_rendering.py
- test_upload_jobs.py
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
- clip_prescore.py
- create_app
- Face Detection Core
- Frontend Dependencies
- App Shell Layout
- Crop Plan Geometry
- segmenter.py
- Face Tracking Frames
- Speaker Tracking Results
- _get_source_or_404
- speaker_tracking.py
- Landing Page UI
- Frontend TypeScript Config
- lifespan
- routes_sources.py
- bench_selection.py
- Project Docs Concepts
- api_error
- SegmenterWorkspace
- Frontend API Client
- compact_selection.py
- interpolate_crop
- config.py
- SegmenterWorkspace.tsx
- Design System: ClipForge
- routes_jobs.py
- PostCSS Config
- Backend Package Meta
- test_sources.py
- test_hardening.py
- CompactOllamaClipSelector
- Product
- test_captions.py
- build_compact_schema
- SampledFrame

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

## Communities (75 total, 31 thin omitted)

### Community 0 - "test_rendering.py"
Cohesion: 0.05
Nodes (41): sample_clip_frames(), _extract_rotation(), MediaInfo, MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), build_crop_commands_file() (+33 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.07
Nodes (34): _check_upload_preconditions(), create_source(), create_job(), reject_oversized_upload(), EmptyUpload, file_extension(), human_size(), remove_tree() (+26 more)

### Community 2 - "Job"
Cohesion: 0.10
Nodes (12): create_source_segment(), Job, JobKind, JobState, JobRead, claim_next_queued_job(), recover_interrupted_jobs(), _job() (+4 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.07
Nodes (26): TranscriptWord, build_transcript(), _clamp(), extract_audio(), _finite_float(), is_non_speech_text(), load_transcript(), _load_whisper_model() (+18 more)

### Community 4 - "main.py"
Cohesion: 0.12
Nodes (13): health(), get_settings(), _configure_logging(), HealthCheck, HealthLimits, HealthResponse, check_face_detection(), check_media_tools() (+5 more)

### Community 5 - "pipeline.py"
Cohesion: 0.07
Nodes (24): ClipSelector, ClipRenderer, SpeakerTracker, FasterWhisperTranscriber, save_transcript(), Transcriber, unload_whisper_models(), CancelToken (+16 more)

### Community 6 - "conftest.py"
Cohesion: 0.22
Nodes (17): command_exists(), app(), audio_only_file(), failing_client(), failing_renderer_client(), failing_selector_client(), failing_tracker_client(), _ffmpeg_command() (+9 more)

### Community 7 - "Frontend UI Components"
Cohesion: 0.12
Nodes (34): JobPage(), AlertIcon(), CheckIcon(), CopyIcon(), DownloadIcon(), FileVideoIcon(), SpinnerIcon(), XIcon() (+26 more)

### Community 8 - "test_upload_jobs.py"
Cohesion: 0.13
Nodes (14): test_clip_file_requires_completed_render(), test_clip_list_is_empty_in_phase_one(), test_job_record_survives_app_restart(), test_long_video_produces_candidate_clips(), test_rendering_failure_marks_clip_failed(), test_tracking_failure_keeps_job_and_centres_crop(), test_upload_rejects_file_without_video_stream(), test_upload_rejects_oversized_file() (+6 more)

### Community 9 - "Settings"
Cohesion: 0.11
Nodes (5): Settings, job_directories(), _safe_child(), ensure_data_dirs(), _job_dirs()

### Community 10 - "services/clip_selection.py"
Cohesion: 0.05
Nodes (61): LLMClip, LLMClipScores, LLMClipSelection, build_candidate(), build_chunks(), build_response_schema(), candidates_from_payload(), _clamp() (+53 more)

### Community 11 - "generate_candidate_regions"
Cohesion: 0.11
Nodes (27): build_units(), flush(), _describe(), generate_candidate_regions(), target_candidate_count(), TranscriptUnit, _unit_text(), _word_count() (+19 more)

### Community 12 - "clip_prescore.py"
Cohesion: 0.25
Nodes (10): CandidateRegion, _clamp(), _containment(), _gap(), distinct(), _iou(), _is_number_token(), _overlap() (+2 more)

### Community 13 - "create_app"
Cohesion: 0.18
Nodes (9): create_app(), cleanup_orphan_job_dirs(), client(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_delete_active_job_cancels_worker_and_removes_media(), test_delete_queued_job_removes_upload_without_worker(), test_delete_unknown_or_repeated_job_returns_404(), test_upload_rejects_when_free_disk_is_below_minimum() (+1 more)

### Community 14 - "Face Detection Core"
Cohesion: 0.10
Nodes (8): create_face_detector(), FaceDetectionError, FaceDetector, OpenCVYuNetDetector, OpenCVSpeakerTracker, test_missing_face_model_raises_actionable_error(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

### Community 15 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (25): dependencies, next@16.4.5, react@19.3.1, react-dom@19.3.1, devDependencies, tailwindcss@4.3.5, @tailwindcss/postcss@4.3.5, @types/node@26.6.6 (+17 more)

### Community 16 - "App Shell Layout"
Cohesion: 0.10
Nodes (18): nextConfig, archivo, metadata, robotoMono, RootLayout(), viewport, AppShell(), NavItem (+10 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.18
Nodes (9): FaceBox, build_crop_plan(), summarize_choices(), TrackChoice, test_crop_plan_interpolates_between_samples(), test_dead_zone_ignores_tiny_movement(), test_missing_face_holds_then_centres(), test_speed_limit_caps_crop_jumps() (+1 more)

### Community 18 - "segmenter.py"
Cohesion: 0.15
Nodes (14): _apply_progress(), _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), _probe_output(), process_segmenter_job() (+6 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.16
Nodes (16): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, FrameFaces, _face(), _frame() (+8 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 23 - "_get_source_or_404"
Cohesion: 0.20
Nodes (16): _cue_payload(), download_source_captions_srt(), download_source_captions_txt(), get_source(), get_source_caption_range(), get_source_captions(), _get_source_or_404(), get_source_transcript() (+8 more)

### Community 24 - "speaker_tracking.py"
Cohesion: 0.17
Nodes (11): _association_score(), _centrality(), choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, is_speech_active(), _median() (+3 more)

### Community 27 - "Landing Page UI"
Cohesion: 0.18
Nodes (16): NotFound(), AIClipperPage(), steps, ArrowRightIcon(), RegMarks(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady() (+8 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "lifespan"
Cohesion: 0.10
Nodes (8): _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), lifespan(), JobWorker, test_additive_migration_adds_phase4_clip_columns()

### Community 30 - "routes_sources.py"
Cohesion: 0.15
Nodes (10): delete_source(), _run_source_transcription(), delete_job_files(), delete_source_files(), is_job_uuid(), job_clips_dir(), job_upload_dir(), job_work_dir() (+2 more)

### Community 31 - "bench_selection.py"
Cohesion: 0.14
Nodes (7): create_clip_selector(), estimate_tokens(), build_settings(), main(), TrackingClient, test_factory_keeps_legacy_selector_behind_config(), test_factory_returns_compact_selector_by_default()

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "api_error"
Cohesion: 0.13
Nodes (20): api_error(), _cue_payload(), get_clip(), get_clip_captions(), get_clip_file(), _get_clip_or_404(), _resolve_transcript_for_clip(), _caption_filename() (+12 more)

### Community 36 - "SegmenterWorkspace"
Cohesion: 0.18
Nodes (16): SegmenterPage(), specimens, ScissorsIcon(), copyToClipboard(), cueText(), rangeCaptionText(), SegmenterWorkspace(), handleCopyCaptionText() (+8 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.21
Nodes (24): handleGenerateTranscript(), handleGenerateTranscript(), API_BASE_URL, ApiError, createSegmenterJob(), createSource(), createSourceSegment(), deleteJob() (+16 more)

### Community 39 - "compact_selection.py"
Cohesion: 0.12
Nodes (27): CompactClipProposal, build_compact_candidate(), candidates_from_compact_payload(), _clamp(), _clean_category(), _clean_hook(), find_region(), fit_within_region() (+19 more)

### Community 40 - "interpolate_crop"
Cohesion: 0.20
Nodes (4): CropPlan, CropSample, interpolate_crop(), SpeakerTrackingError

### Community 41 - "config.py"
Cohesion: 0.08
Nodes (11): _count(), _model_is_available(), _normalize_model_name(), OllamaChatResult, OllamaClient, OllamaProbe, _parse_chat_stats(), _seconds() (+3 more)

### Community 44 - "SegmenterWorkspace.tsx"
Cohesion: 0.14
Nodes (16): CaptionPreview, FALLBACK_FORMATS, ParsedRange, parseRanges(), parseTimestamp(), loadCaptionPreview(), CaptionCue, CaptionDefaults (+8 more)

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "routes_jobs.py"
Cohesion: 0.11
Nodes (5): get_session(), Base, Clip, ClipRead, utc_now()

### Community 57 - "test_sources.py"
Cohesion: 0.29
Nodes (7): Source, _create_source(), _cut(), test_multiple_cuts_reuse_one_source_and_survive_job_deletion(), test_source_segment_validation(), test_source_upload_creates_project_without_a_job(), test_unknown_source_returns_404()

### Community 62 - "test_hardening.py"
Cohesion: 0.11
Nodes (10): JobCancelled, BlockingTranscriber, _clip_row(), _job_row(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_completed_job_removes_record_clips_and_media(), test_delete_job_files_refuses_non_uuid_ids(), test_job_state_cancelled_is_terminal() (+2 more)

### Community 63 - "CompactOllamaClipSelector"
Cohesion: 0.09
Nodes (23): ClipSelectionError, CompactOllamaClipSelector, load_compact_instructions(), log_selection_timings(), SelectionTimings, OllamaChatStats, OllamaError, OllamaMalformedResponse (+15 more)

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 71 - "test_captions.py"
Cohesion: 0.06
Nodes (58): Transcript, TranscriptSegment, _apply_romanization(), CaptionCue, captions_for_range(), captions_for_transcript(), captions_to_plain_text(), CaptionWord (+50 more)

### Community 76 - "SampledFrame"
Cohesion: 0.33
Nodes (3): SampledFrame, _FakeDetector, test_tracker_orchestration_builds_a_crop_plan()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 459 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `test_rendering.py`, `test_upload_jobs.py`, `test_transcript.py`, `main.py`, `pipeline.py`, `conftest.py`, `test_upload_jobs.py`, `services/clip_selection.py`, `generate_candidate_regions`, `clip_prescore.py`, `create_app`, `Face Detection Core`, `Crop Plan Geometry`, `segmenter.py`, `Face Tracking Frames`, `Speaker Tracking Results`, `speaker_tracking.py`, `lifespan`, `routes_sources.py`, `bench_selection.py`, `compact_selection.py`, `config.py`, `routes_jobs.py`, `test_hardening.py`, `CompactOllamaClipSelector`, `SampledFrame`?**
  _High betweenness centrality (0.284) - this node is a cross-community bridge._
- **Are the 153 inferred relationships involving `Settings` (e.g. with `health()` and `cleanup_orphan_job_dirs()`) actually correct?**
  _`Settings` has 153 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_rendering.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05043859649122807 - nodes in this community are weakly interconnected._
- **Why does `Transcript` connect `test_captions.py` to `api_error`, `test_transcript.py`, `pipeline.py`, `compact_selection.py`, `services/clip_selection.py`, `routes_jobs.py`, `Face Detection Core`, `Speaker Tracking Results`, `_get_source_or_404`, `speaker_tracking.py`, `bench_selection.py`, `routes_sources.py`, `CompactOllamaClipSelector`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `Job` (e.g. with `_resolve_transcript_for_clip()` and `_caption_filename()`) actually correct?**
  _`Job` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07005649717514124 - nodes in this community are weakly interconnected._