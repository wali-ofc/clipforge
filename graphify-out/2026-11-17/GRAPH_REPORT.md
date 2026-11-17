# Graph Report - clipforge  (2026-11-17)

## Corpus Check
- 94 files · ~58,609 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .log 6, .example 2, (none) 2)

## Summary
- 1110 nodes · 3103 edges · 74 communities (48 shown, 26 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 325 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `88149412`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FFmpeg Clip Rendering
- test_upload_jobs.py
- conftest.py
- test_transcript.py
- main.py
- pipeline.py
- CancelToken
- Frontend UI Components
- Settings
- FFmpeg Command Helpers
- services/clip_selection.py
- Clip Selection Schemas
- Transcript
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
- Design System: ClipForge
- routes_clips.py
- ClipSelector
- PostCSS Config
- Backend Package Meta
- .transcribe
- create_job
- .render_clip
- .render_clip
- Product
- routes_upload.py
- _sanitize_segment
- transcription.py
- job_directories
- is_non_speech_text
- sanitize_display_filename
- surface-brief-body.md
- frontend-src-app-page-tsx.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 176 edges
2. `Job` - 38 edges
3. `create_app()` - 37 edges
4. `process_job()` - 37 edges
5. `JobState` - 34 edges
6. `Transcript` - 33 edges
7. `JobStatusView()` - 32 edges
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

## Communities (74 total, 26 thin omitted)

### Community 0 - "FFmpeg Clip Rendering"
Cohesion: 0.16
Nodes (13): MediaInfo, build_crop_commands_file(), RenderingError, _verify_output(), _media_info(), test_build_crop_commands_centers_without_plan(), test_build_crop_commands_clamps_and_dedupes(), test_build_crop_commands_file() (+5 more)

### Community 1 - "test_upload_jobs.py"
Cohesion: 0.09
Nodes (30): test_clip_duration_range_is_validated(), test_clip_hard_range_must_wrap_target_range(), test_clip_score_weights_are_normalized(), test_clip_score_weights_reject_negative_and_zero_totals(), test_clip_score_weights_require_exact_keys(), test_clip_window_overlap_must_be_smaller_than_window(), test_empty_whisper_model_is_rejected(), test_extensions_are_normalized_and_deduplicated() (+22 more)

### Community 2 - "conftest.py"
Cohesion: 0.17
Nodes (19): get_settings(), command_exists(), app(), audio_only_file(), client(), failing_client(), failing_renderer_client(), failing_selector_client() (+11 more)

### Community 3 - "test_transcript.py"
Cohesion: 0.18
Nodes (14): build_transcript(), load_transcript(), _FakeModel, _raw_segment(), test_build_transcript_clamps_and_drops_invalid_ranges(), test_build_transcript_keeps_absolute_timestamps_and_words(), test_build_transcript_sorts_segments_by_start(), test_build_transcript_without_speech_discards_language_guess() (+6 more)

### Community 4 - "main.py"
Cohesion: 0.06
Nodes (21): health(), _apply_sqlite_additive_migrations(), create_engine_from_settings(), create_session_factory(), ensure_sqlite_directory(), init_db(), _configure_logging(), create_app() (+13 more)

### Community 5 - "pipeline.py"
Cohesion: 0.16
Nodes (13): Transcriber, job_clips_dir(), job_work_dir(), relative_to_data_dir(), _check_cancelled(), _cleanup_temp_files(), _mark_cancelled(), _mark_failed() (+5 more)

### Community 6 - "CancelToken"
Cohesion: 0.10
Nodes (6): CancelToken, JobCancelled, _raise_if_cancelled(), on_stage(), BlockingTranscriber, test_process_job_marks_preexisting_cancellation()

### Community 7 - "Frontend UI Components"
Cohesion: 0.16
Nodes (22): JobPage(), DownloadIcon(), FileVideoIcon(), badgeClasses(), ClipCard(), Detail(), fallbackNote(), JobStatusView() (+14 more)

### Community 8 - "Settings"
Cohesion: 0.12
Nodes (7): Settings, cleanup_orphan_job_dirs(), ensure_data_dirs(), job_upload_dir(), _job_dirs(), test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(), test_delete_active_job_cancels_worker_and_removes_media()

### Community 9 - "FFmpeg Command Helpers"
Cohesion: 0.13
Nodes (8): CommandCancelled, CommandError, CommandNotFoundError, _run_cancellable(), run_command(), _terminate(), test_run_command_stops_promptly_when_cancelled(), fake_run()

### Community 10 - "services/clip_selection.py"
Cohesion: 0.11
Nodes (18): TranscriptSegment, TranscriptWord, build_candidate(), candidates_from_payload(), _clamp(), _clean_text(), _conciseness(), _finite_float() (+10 more)

### Community 11 - "Clip Selection Schemas"
Cohesion: 0.15
Nodes (17): LLMClip, LLMClipScores, LLMClipSelection, build_response_schema(), score_candidate(), TranscriptChunk, _payload(), _segment() (+9 more)

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
Cohesion: 0.10
Nodes (18): nextConfig, archivo, metadata, robotoMono, RootLayout(), viewport, AppShell(), NavItem (+10 more)

### Community 17 - "Crop Plan Geometry"
Cohesion: 0.12
Nodes (12): FaceBox, _association_score(), build_crop_plan(), _centrality(), summarize_choices(), TrackChoice, _FakeDetector, test_crop_plan_interpolates_between_samples() (+4 more)

### Community 18 - "Transcript Segment Fitting"
Cohesion: 0.16
Nodes (13): _apply_progress(), _concat_parts(), _even_floor(), _format_ts(), parse_segment_spec(), parse_timestamp(), process_segmenter_job(), _render_range() (+5 more)

### Community 19 - "Face Tracking Frames"
Cohesion: 0.18
Nodes (15): assign_mouth_motion(), build_face_tracks(), compute_crop_geometry(), CropGeometry, FrameFace, _face(), _frame(), test_exact_portrait_source_is_not_cropped() (+7 more)

### Community 20 - "Speaker Tracking Results"
Cohesion: 0.13
Nodes (11): build_centered_result(), build_speech_intervals(), _centered_plan(), _extract_mouth_patch(), _load_frame(), _report(), SpeakerTrackingResult, _target_aspect() (+3 more)

### Community 21 - "pathlib"
Cohesion: 0.15
Nodes (12): reject_oversized_upload(), EmptyUpload, file_extension(), human_size(), stream_upload_to_path(), UploadTooLarge, test_file_extension_is_lowercase(), test_human_size() (+4 more)

### Community 23 - "Media Probe Service"
Cohesion: 0.20
Nodes (10): _extract_rotation(), MediaProbeError, _parse_float(), _parse_frame_rate(), probe_media(), _probe_output(), test_probe_reads_valid_sample(), test_probe_rejects_audio_only_file() (+2 more)

### Community 24 - "speaker_tracking.py"
Cohesion: 0.20
Nodes (10): choose_active_tracks(), _clamp(), _clamp_center(), FaceTrack, FrameFaces, is_speech_active(), _median(), _track_stats() (+2 more)

### Community 25 - "face_detection.py"
Cohesion: 0.15
Nodes (7): FaceDetectionError, sample_clip_frames(), SampledFrame, OpenCVSpeakerTracker, test_tracker_orchestration_builds_a_crop_plan(), test_tracker_returns_explicit_centred_result_when_model_is_missing(), factory()

### Community 27 - "Landing Page UI"
Cohesion: 0.17
Nodes (19): NotFound(), AIClipperPage(), steps, AlertIcon(), ArrowRightIcon(), CheckIcon(), RegMarks(), SpinnerIcon() (+11 more)

### Community 28 - "Frontend TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 29 - "Job and Clip Models"
Cohesion: 0.17
Nodes (13): Job, JobState, apply_progress(), claim_next_queued_job(), _select_clips_with_progress(), on_progress(), on_progress(), recover_interrupted_jobs() (+5 more)

### Community 30 - "routes_upload.py"
Cohesion: 0.12
Nodes (6): Base, Clip, JobKind, JobRead, utc_now(), _clip_row()

### Community 31 - "test_hardening.py"
Cohesion: 0.18
Nodes (9): _job_row(), test_clip_file_endpoint_rejects_unsafe_stored_path(), test_delete_completed_job_removes_record_clips_and_media(), test_delete_queued_job_removes_upload_without_worker(), test_delete_unknown_or_repeated_job_returns_404(), test_job_state_cancelled_is_terminal(), test_transcript_endpoint_rejects_unsafe_stored_path(), test_upload_rejects_when_free_disk_is_below_minimum() (+1 more)

### Community 32 - "Clip Candidate Scoring"
Cohesion: 0.25
Nodes (10): ClipCandidate, _containment(), deduplicate_candidates(), _iou(), test_deduplication_keeps_highest_score_and_limits_count(), candidate(), test_deduplication_prefers_shorter_clip_on_score_tie(), candidate() (+2 more)

### Community 33 - "Project Docs Concepts"
Cohesion: 0.16
Nodes (15): Graphify workflow guidance for ClipForge, Clip selection prompt template, Pinned backend dependency set, Frontend Next.js agent guidance, API and results experience, LLM clip selection via Ollama, ClipForge local-first AI video clipping, ClipForge processing pipeline (+7 more)

### Community 35 - "Job API Operations"
Cohesion: 0.20
Nodes (6): api_error(), delete_job(), get_job(), _get_job_or_404(), get_job_transcript(), list_job_clips()

### Community 36 - "Segmenter UI Flow"
Cohesion: 0.23
Nodes (13): SegmenterPage(), specimens, ScissorsIcon(), UploadCloudIcon(), FALLBACK_FORMATS, mediaToolsReady(), SegmenterForm(), handleDrop() (+5 more)

### Community 37 - "Frontend API Client"
Cohesion: 0.37
Nodes (12): API_BASE_URL, ApiError, createSegmenterJob(), deleteJob(), errorFromResponse(), getHealth(), getJob(), getJobClips() (+4 more)

### Community 39 - "Ollama Client Probe"
Cohesion: 0.17
Nodes (4): _model_is_available(), _normalize_model_name(), OllamaClient, OllamaProbe

### Community 40 - "interpolate_crop"
Cohesion: 0.20
Nodes (4): CropPlan, CropSample, interpolate_crop(), SpeakerTrackingError

### Community 42 - "Clip Selection Logic"
Cohesion: 0.14
Nodes (8): build_chunks(), ClipSelectionError, load_prompt_template(), render_prompt(), _settings(), test_chunks_use_overlapping_absolute_windows(), test_prompt_contains_absolute_timestamps_and_limits(), test_prompt_placeholder_error_is_actionable()

### Community 44 - "API Shared Types"
Cohesion: 0.25
Nodes (7): Clip, CropPlan, CropPlanSample, Health, HealthCheck, Job, JobKind

### Community 45 - "Design System: ClipForge"
Cohesion: 0.09
Nodes (21): Badges, Buttons, Colors, Components, Design System: ClipForge, Do:, Do's and Don'ts, Don't: (+13 more)

### Community 46 - "routes_clips.py"
Cohesion: 0.20
Nodes (5): get_clip(), get_clip_file(), _get_clip_or_404(), ClipRead, resolve_stored_path()

### Community 48 - "ClipSelector"
Cohesion: 0.14
Nodes (3): ClipSelector, ClipRenderer, SpeakerTracker

### Community 57 - ".transcribe"
Cohesion: 0.18
Nodes (5): extract_audio(), _load_whisper_model(), _report(), _report_stage(), TranscriptionError

### Community 58 - "create_job"
Cohesion: 0.17
Nodes (4): create_job(), delete_job_files(), remove_tree(), test_delete_job_files_refuses_non_uuid_ids()

### Community 59 - ".render_clip"
Cohesion: 0.20
Nodes (3): format_sendcmd_path(), RenderResult, test_format_sendcmd_path()

### Community 60 - ".render_clip"
Cohesion: 0.24
Nodes (8): _even(), FFmpegClipRenderer, _require_ffmpeg(), test_dynamic_crop_follows_plan(), test_ffmpeg_clip_renderer_integration(), test_ffmpeg_clip_renderer_without_audio(), test_renderer_missing_source(), test_renderer_removes_partial_output_on_ffmpeg_failure()

### Community 65 - "Product"
Cohesion: 0.15
Nodes (12): Accessibility & Inclusion, Brand Commitments, Capabilities and Constraints, Evidence on Hand, Operating Context, Platform, Positioning, Product (+4 more)

### Community 67 - "_sanitize_segment"
Cohesion: 0.33
Nodes (5): _clamp(), FasterWhisperTranscriber, _finite_float(), _sanitize_segment(), _sanitize_word()

### Community 69 - "job_directories"
Cohesion: 0.33
Nodes (3): is_job_uuid(), job_directories(), _safe_child()

## Knowledge Gaps
- **5 isolated node(s):** `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance`, `Ollama timeout behavior and tuning guidance`, `Clip selection prompt template`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 390 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `FFmpeg Clip Rendering`, `test_upload_jobs.py`, `conftest.py`, `test_transcript.py`, `main.py`, `pipeline.py`, `services/clip_selection.py`, `Clip Selection Schemas`, `Ollama Selection Client`, `Face Detection Core`, `Crop Plan Geometry`, `Transcript Segment Fitting`, `Face Tracking Frames`, `Speaker Tracking Results`, `pathlib`, `Media Probe Service`, `speaker_tracking.py`, `face_detection.py`, `Job and Clip Models`, `test_hardening.py`, `Clip Candidate Scoring`, `Ollama Client Probe`, `Clip Selection Logic`, `routes_clips.py`, `ClipSelector`, `.transcribe`, `create_job`, `.render_clip`, `.render_clip`, `routes_upload.py`, `_sanitize_segment`, `transcription.py`, `job_directories`?**
  _High betweenness centrality (0.270) - this node is a cross-community bridge._
- **Are the 104 inferred relationships involving `Settings` (e.g. with `health()` and `_configure_logging()`) actually correct?**
  _`Settings` has 104 INFERRED edges - model-reasoned connections that need verification._
- **What connects `clipforge-backend`, `Graphify workflow guidance for ClipForge`, `Frontend Next.js agent guidance` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_upload_jobs.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08748615725359911 - nodes in this community are weakly interconnected._
- **Why does `JobWorker` connect `main.py` to `ClipSelector`, `Settings`, `pipeline.py`, `CancelToken`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `Job` (e.g. with `delete_job()` and `get_job()`) actually correct?**
  _`Job` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06247086247086247 - nodes in this community are weakly interconnected._