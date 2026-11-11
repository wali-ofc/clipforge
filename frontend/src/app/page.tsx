import {
  CpuIcon,
  FileVideoIcon,
  ShieldIcon,
} from "@/components/icons";
import { SiteFooter, SiteHeader } from "@/components/SiteHeader";
import { UploadForm } from "@/components/UploadForm";

const features = [
  {
    icon: ShieldIcon,
    title: "Local by default",
    body: "Uploads and generated media stay on this machine.",
  },
  {
    icon: CpuIcon,
    title: "CPU-first",
    body: "Small models and one job at a time on 16 GB machines.",
  },
  {
    icon: FileVideoIcon,
    title: "Portrait output",
    body: "9:16 clips with speaker-aware framing, previewable and downloadable.",
  },
];

const pipeline = [
  { label: "Upload", note: "live", active: true },
  { label: "Transcribe", note: "live", active: true },
  { label: "Select moments", note: "live", active: true },
  { label: "Track & render", note: "live", active: true },
];

export default function HomePage() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 h-[580px] w-[1100px] -translate-x-1/2 rounded-full bg-forge-500/[0.045] blur-3xl"
      />
      <SiteHeader />

      <main className="relative mx-auto w-full max-w-6xl flex-1 px-5 pb-14 sm:px-8">
        <section className="grid gap-10 pb-10 pt-6 lg:grid-cols-[1.03fr_0.97fr] lg:items-start lg:gap-14 lg:pb-16 lg:pt-12">
          <div className="reveal lg:pt-7">
            <div className="inline-flex items-center gap-2 rounded-full border border-forge-500/20 bg-forge-500/[0.06] px-3 py-1.5 text-[11px] font-medium text-forge-200">
              <span className="status-dot h-1.5 w-1.5 rounded-full bg-forge-400" />
              Phase 6 · results &amp; downloads
            </div>

            <h1 className="mt-6 text-balance text-[2.7rem] font-semibold leading-[1.02] tracking-[-0.045em] text-zinc-50 sm:text-6xl">
              Long videos in.
              <br />
              <span className="bg-gradient-to-r from-forge-200 via-forge-300 to-forge-500 bg-clip-text text-transparent">
                Sharp clips out.
              </span>
            </h1>

            <p className="mt-5 max-w-lg text-[15px] leading-7 text-zinc-400">
              A local-first pipeline for turning long recordings into short
              vertical moments. No cloud processing, no accounts, no per-minute
              fees.
            </p>
            <p className="mt-3 max-w-lg text-sm leading-6 text-zinc-500">
              This build validates your upload, transcribes the audio locally
              with Whisper, asks a local Ollama model for self-contained
              moments, then tracks the likely speaker and renders each clip as
              a 9:16 portrait MP4. Preview and download the results in the
              browser.
            </p>

            <dl className="mt-8 grid gap-3 sm:grid-cols-3">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-3.5"
                >
                  <dt className="flex items-center gap-2 text-xs font-medium text-zinc-200">
                    <feature.icon className="h-4 w-4 text-forge-300" />
                    {feature.title}
                  </dt>
                  <dd className="mt-2 text-[11px] leading-5 text-zinc-500">
                    {feature.body}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="reveal reveal-1">
            <UploadForm />
          </div>
        </section>

        <section className="reveal reveal-2 rounded-2xl border border-white/[0.07] bg-surface-900/45 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-600">
                Pipeline
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                Each phase is tested before the next one starts.
              </p>
            </div>
            <ol className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-1.5">
              {pipeline.map((step, index) => (
                <li
                  key={step.label}
                  className="flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2 text-[11px]"
                >
                  <span
                    className={[
                      "flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-semibold",
                      step.active
                        ? "bg-forge-500 text-[#1b0d04]"
                        : "bg-white/[0.06] text-zinc-500",
                    ].join(" ")}
                  >
                    {index + 1}
                  </span>
                  <span
                    className={
                      step.active ? "font-medium text-zinc-200" : "text-zinc-500"
                    }
                  >
                    {step.label}
                  </span>
                  <span className="text-[9px] uppercase tracking-[0.12em] text-zinc-700">
                    {step.note}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
