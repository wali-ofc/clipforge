import { ScissorsIcon } from "@/components/icons";
import { SegmenterForm } from "@/components/SegmenterForm";

export default function SegmenterPage() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-line bg-paper-50/70 px-5 py-4 sm:px-8">
        <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-teal-700">
          <ScissorsIcon className="h-3.5 w-3.5" />
          Segmenter
        </p>
        <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em] text-ink-900 sm:text-xl">
          Cut and join clips by timestamp
        </h1>
        <p className="mt-1 max-w-2xl text-xs leading-5 text-ink-500">
          Upload a video, provide time ranges, and download each segment as its own clip — or join comma-separated ranges into a single clip.
        </p>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 pb-14 pt-6 sm:px-8">
        <section className="grid gap-10 lg:grid-cols-[1fr_1.05fr] lg:items-start lg:gap-14">
          <div className="lg:pt-2">
            <h2 className="text-balance text-[2rem] font-semibold leading-[1.08] tracking-[-0.035em] text-ink-900 sm:text-4xl">
              Precise cuts.
              <br />
              <span className="text-teal-600">No AI guessing.</span>
            </h2>
            <p className="mt-4 max-w-lg text-[15px] leading-7 text-ink-700">
              Segmenter trims exactly the ranges you specify. Use it to extract highlights, remove sections, or stitch multiple moments together.
            </p>

            <div className="mt-6 space-y-3">
              <div className="rounded-xl border border-line bg-white p-4">
                <p className="text-xs font-semibold text-ink-900">Separate clips</p>
                <p className="mt-1 text-[11px] leading-5 text-ink-500">
                  Put each range on a new line to get individual downloadable clips.
                </p>
                <pre className="mt-2 overflow-x-auto rounded-lg border border-line bg-paper-50 px-3 py-2 font-mono text-[11px] leading-5 text-ink-700">{`1:23 - 2:23
5:23 - 6:32`}</pre>
              </div>
              <div className="rounded-xl border border-line bg-white p-4">
                <p className="text-xs font-semibold text-ink-900">Join into one clip</p>
                <p className="mt-1 text-[11px] leading-5 text-ink-500">
                  Use commas in the same line/group to cut those parts and join them into a single clip.
                </p>
                <pre className="mt-2 overflow-x-auto rounded-lg border border-line bg-paper-50 px-3 py-2 font-mono text-[11px] leading-5 text-ink-700">{`1:23 - 2:23, 5:23 - 6:32`}</pre>
              </div>
              <div className="rounded-xl border border-teal-100 bg-teal-50/60 p-4">
                <p className="text-xs font-semibold text-teal-800">Frame toggle</p>
                <p className="mt-1 text-[11px] leading-5 text-teal-700">
                  Keep the original framing, or switch to a centered 9:16 portrait crop for vertical outputs.
                </p>
              </div>
            </div>
          </div>

          <div>
            <SegmenterForm />
          </div>
        </section>
      </main>
    </div>
  );
}