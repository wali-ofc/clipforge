import { RegMarks } from "@/components/icons";
import { UploadForm } from "@/components/UploadForm";

const steps = [
  {
    title: "Inspect",
    body: "The file is probed on disk before anything runs.",
  },
  {
    title: "Transcribe",
    body: "Whisper finds words and timestamps locally.",
  },
  {
    title: "Select",
    body: "A local model proposes self-contained moments.",
  },
  {
    title: "Render",
    body: "Speaker-aware crops become verified 9:16 MP4s.",
  },
];

export default function AIClipperPage() {
  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper-0 px-5 py-3 sm:px-8">
        <p className="mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
          ClipForge / Local video workshop
        </p>
        <div className="hidden items-center gap-4 sm:flex">
          <span className="mono text-[10px] uppercase tracking-[0.16em] text-ink-400">
            Tool 01 — AI Clipper
          </span>
          <span className="tally tally--live text-ink-600">Local</span>
        </div>
      </div>

      <main className="mx-auto w-full max-w-[1180px] flex-1 px-5 pb-12 pt-8 sm:px-8 sm:pt-12">
        <section className="grid gap-10 lg:grid-cols-[1.02fr_0.98fr] lg:items-start lg:gap-16">
          <div className="lg:pt-3">
            <h1 className="display">
              Long video in.
              <br />
              <span className="signal">Short clips out.</span>
            </h1>

            <p className="lede mt-7">
              A local-first pipeline that turns a long video into short vertical
              moments. No cloud processing, no accounts, and no per-minute fees —
              every stage runs on this machine.
            </p>
            <p className="note mt-4">
              Upload a recording, review the job as it moves through each stage,
              then preview and download the finished clips from the browser.
            </p>

            <div className="mt-9 grid grid-cols-1 border-y border-line sm:grid-cols-3">
              <div className="border-b border-line py-3 sm:border-b-0 sm:border-r sm:pr-3">
                <p className="mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-900">
                  Local only
                </p>
                <p className="mt-1 text-[11px] leading-4 text-ink-500">
                  Files never leave this machine
                </p>
              </div>
              <div className="border-b border-line py-3 sm:border-b-0 sm:border-r sm:pl-3 sm:pr-3">
                <p className="mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-900">
                  CPU-first
                </p>
                <p className="mt-1 text-[11px] leading-4 text-ink-500">
                  Small models, one job at a time
                </p>
              </div>
              <div className="py-3 sm:pl-3">
                <p className="mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-900">
                  9:16 output
                </p>
                <p className="mt-1 text-[11px] leading-4 text-ink-500">
                  Portrait MP4, previewable
                </p>
              </div>
            </div>

            <ol className="mt-8">
              {steps.map((step, index) => (
                <li
                  key={step.title}
                  className="flex gap-4 border-b border-line py-3 last:border-b-0"
                >
                  <span className="data w-6 shrink-0 pt-0.5 text-accent-500">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[13px] font-bold tracking-[-0.02em] text-ink-900">
                      {step.title}
                    </span>
                    <span className="mt-0.5 block text-xs leading-5 text-ink-500">
                      {step.body}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </div>

          <div className="sheet relative">
            <RegMarks />
            <div className="sheet-head">
              <span className="meta">Source / 01</span>
              <span className="badge badge-accent">Drop a video</span>
            </div>
            <div className="sheet-body">
              <UploadForm />
            </div>
          </div>
        </section>

        <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-2 border-t border-line pt-5 mono text-[10px] uppercase tracking-[0.12em] text-ink-500">
          <span>Input · .mp4 / .mov / .mkv</span>
          <span aria-hidden="true" className="text-line-strong">/</span>
          <span>Output · 1080×1920 H.264 + AAC</span>
          <span aria-hidden="true" className="text-line-strong">/</span>
          <span>Chain · whisper → ollama → opencv → ffmpeg</span>
        </div>
      </main>
    </div>
  );
}
