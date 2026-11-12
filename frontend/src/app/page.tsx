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
  "Upload",
  "Transcribe",
  "Select moments",
  "Track & render",
];

export default function HomePage() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 pb-14 sm:px-8">
        <section className="grid gap-10 pb-10 pt-6 lg:grid-cols-[1.03fr_0.97fr] lg:items-start lg:gap-14 lg:pb-16 lg:pt-12">
          <div className="lg:pt-7">
            <h1 className="text-balance text-[2.7rem] font-semibold leading-[1.02] tracking-[-0.045em] text-ink-900 sm:text-6xl">
              Long videos in.
              <br />
              <span className="text-teal-600">Sharp clips out.</span>
            </h1>

            <p className="mt-5 max-w-lg text-[15px] leading-7 text-ink-700">
              A local-first pipeline for turning long recordings into short
              vertical moments. No cloud processing, no accounts, no per-minute
              fees.
            </p>
            <p className="mt-3 max-w-lg text-sm leading-6 text-ink-500">
              This build validates your upload, transcribes the audio locally
              with Whisper, asks a local Ollama model for self-contained
              moments, then tracks the likely speaker and renders each clip as
              a 9:16 portrait MP4. Preview and download the results in the
              browser.
            </p>

            <dl className="mt-8 grid divide-y divide-line overflow-hidden rounded-2xl border border-line bg-white sm:grid-cols-3 sm:divide-x sm:divide-y-0">
              {features.map((feature) => (
                <div key={feature.title} className="p-4">
                  <dt className="flex items-center gap-2 text-xs font-semibold text-ink-900">
                    <feature.icon className="h-4 w-4 text-teal-600" />
                    {feature.title}
                  </dt>
                  <dd className="mt-2 text-[11px] leading-5 text-ink-500">
                    {feature.body}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div>
            <UploadForm />
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-white px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-400">
                Pipeline
              </p>
              <p className="mt-1 text-xs text-ink-500">
                Each phase is tested before the next one starts.
              </p>
            </div>
            <ol className="grid grid-cols-2 gap-2 sm:flex sm:items-center sm:gap-1.5">
              {pipeline.map((step, index) => (
                <li
                  key={step}
                  className="flex items-center gap-2 rounded-lg border border-line bg-paper-50 px-2.5 py-2 text-[11px]"
                >
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-teal-50 text-[9px] font-semibold text-teal-700">
                    {index + 1}
                  </span>
                  <span className="font-medium text-ink-800">{step}</span>
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
