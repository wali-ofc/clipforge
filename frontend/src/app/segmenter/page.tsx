import { RegMarks, ScissorsIcon } from "@/components/icons";
import { SegmenterForm } from "@/components/SegmenterForm";

const specimens = [
  {
    label: "Separate clips",
    body: "One range per line becomes its own downloadable clip.",
    value: "1:23 - 2:23\n5:23 - 6:32",
  },
  {
    label: "Joined clip",
    body: "Comma-separated ranges in one line are cut and stitched in order.",
    value: "1:23 - 2:23, 5:23 - 6:32",
  },
];

export default function SegmenterPage() {
  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-paper-0 px-5 py-3 sm:px-8">
        <p className="mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
          ClipForge / Local video workshop
        </p>
        <div className="hidden items-center gap-4 sm:flex">
          <span className="mono text-[10px] uppercase tracking-[0.16em] text-ink-400">
            Tool 02 — Segmenter
          </span>
          <span className="tally tally--live text-ink-600">Local</span>
        </div>
      </div>

      <main className="mx-auto w-full max-w-[1180px] flex-1 px-5 pb-12 pt-8 sm:px-8 sm:pt-12">
        <section className="grid gap-10 lg:grid-cols-[1.02fr_0.98fr] lg:items-start lg:gap-16">
          <div className="lg:pt-3">
            <h1 className="display-sm">
              Precise cuts.
              <br />
              <span className="signal">No AI guessing.</span>
            </h1>

            <p className="lede mt-6">
              Segmenter trims exactly the ranges you specify. Extract highlights,
              remove sections, or stitch several moments into a single clip —
              all on this machine.
            </p>

            <div className="mt-9 border-t border-line">
              {specimens.map((specimen, index) => (
                <div
                  key={specimen.label}
                  className="border-b border-line py-4"
                >
                  <div className="flex items-baseline justify-between gap-4">
                    <h2 className="text-[13px] font-bold tracking-[-0.02em] text-ink-900">
                      {specimen.label}
                    </h2>
                    <span className="data text-ink-400">
                      0{index + 1}
                    </span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-ink-500">
                    {specimen.body}
                  </p>
                  <pre className="mt-3 overflow-x-auto border-l-2 border-accent-500 bg-paper-200/60 px-3 py-2 font-mono text-[11px] leading-5 text-ink-800">
{specimen.value}
                  </pre>
                </div>
              ))}
            </div>

            <p className="note mt-5 flex items-start gap-2">
              <ScissorsIcon className="mt-0.5 h-4 w-4 shrink-0 text-accent-500" />
              <span>
                Choose the original frame or a centred 9:16 portrait crop for
                each job. Output is always an H.264/AAC MP4.
              </span>
            </p>
          </div>

          <div className="sheet relative">
            <RegMarks />
            <div className="sheet-head">
              <span className="meta">Source / 02</span>
              <span className="badge badge-accent">Drop a video</span>
            </div>
            <div className="sheet-body">
              <SegmenterForm />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
