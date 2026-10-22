import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Play,
} from "lucide-react"
import { Link } from "react-router-dom"

import {
  getEvalRuns,
  getEvalScenarios,
  getGenerationEval,
  getGenerationEvals,
  openEvalReport,
  startEvalRun,
  type EvalRun,
  type GenerationEvalRecord,
} from "@/api/evals"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

type Tab = "benchmark" | "generations"

const percent = (value: number | null | undefined) =>
  typeof value === "number" ? `${Math.round(value * 100)}%` : "—"

const seconds = (value: number | null | undefined) =>
  typeof value === "number" ? `${value.toFixed(1)}s` : "—"

const when = (value: string | null | undefined) =>
  value ? new Date(value).toLocaleString() : "—"

function EvalsPage() {
  const [tab, setTab] = useState<Tab>("benchmark")

  return (
    <div className="min-h-dvh bg-canvas">
      <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-8">
        <Link
          to="/workspaces"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-steel hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Workspaces
        </Link>

        <header className="mb-6">
          <p className="text-xs font-medium tracking-[0.08em] text-steel">
            Development only
          </p>
          <h1 className="mt-1 font-display text-3xl leading-tight text-ink">
            Evaluation
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-body">
            Every BRD is scored automatically when it is generated. The
            benchmark replays curated scenarios against their answer keys to
            measure what the automatic check cannot: whether the document
            captured what the sources said.
          </p>
        </header>

        <div
          role="tablist"
          aria-label="Evaluation views"
          className="mb-6 flex gap-1 border-b border-hairline"
        >
          {(
            [
              ["benchmark", "Benchmark"],
              ["generations", "Your generations"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={
                tab === id
                  ? "-mb-px border-b-2 border-ink px-3 py-2 text-sm font-medium text-ink"
                  : "-mb-px border-b-2 border-transparent px-3 py-2 text-sm font-medium text-steel hover:text-ink"
              }
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "benchmark" ? <BenchmarkTab /> : <GenerationsTab />}
      </main>
    </div>
  )
}

function BenchmarkTab() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<string[] | null>(null)
  const [live, setLive] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const scenariosQuery = useQuery({
    queryKey: ["eval-scenarios"],
    queryFn: getEvalScenarios,
  })

  const runsQuery = useQuery({
    queryKey: ["eval-runs"],
    queryFn: getEvalRuns,
    refetchInterval: (query) =>
      query.state.data?.runs.some((run) => run.status === "running")
        ? 3000
        : false,
  })

  const scenarios = useMemo(
    () => scenariosQuery.data?.scenarios ?? [],
    [scenariosQuery.data],
  )

  const chosen = selected ?? scenarios.map((scenario) => scenario.name)
  const activeRun = runsQuery.data?.runs.find((run) => run.status === "running")

  const runMutation = useMutation({
    mutationFn: () => startEvalRun(chosen, !live),
    onSuccess: () => {
      setConfirming(false)
      void queryClient.invalidateQueries({ queryKey: ["eval-runs"] })
    },
  })

  if (scenariosQuery.isError || runsQuery.isError) {
    return (
      <p role="alert" className="text-sm text-error">
        Could not load evaluation data. Is the backend running with
        ENVIRONMENT=development?
      </p>
    )
  }

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-hairline bg-surface p-5">
        <h2 className="text-sm font-semibold text-ink">Run a benchmark</h2>

        <ul className="mt-4 divide-y divide-hairline">
          {scenarios.map((scenario) => (
            <li
              key={scenario.name}
              className="flex items-center justify-between gap-3 py-2.5"
            >
              <label className="flex min-w-0 items-center gap-2.5 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={chosen.includes(scenario.name)}
                  disabled={Boolean(activeRun)}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked
                        ? [...chosen, scenario.name]
                        : chosen.filter((name) => name !== scenario.name),
                    )
                  }
                  className="size-4 rounded border-edge accent-ink"
                />
                <span className="w-16 shrink-0 text-xs text-steel">
                  {scenario.level}
                </span>
                <span className="truncate">{scenario.name}</span>
              </label>

              <span className="shrink-0 text-xs text-steel">
                {scenario.facts} facts · {scenario.documents} doc
                {scenario.documents === 1 ? "" : "s"} ·{" "}
                {scenario.cached ? "cached" : "not cached"}
              </span>
            </li>
          ))}
        </ul>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-body">
            <input
              type="checkbox"
              checked={live}
              disabled={Boolean(activeRun)}
              onChange={(event) => setLive(event.target.checked)}
              className="size-4 rounded border-edge accent-ink"
            />
            Live run (calls Sarvam — costs credits)
          </label>

          <Button
            variant="default"
            onClick={() => (live ? setConfirming(true) : runMutation.mutate())}
            disabled={Boolean(activeRun) || chosen.length === 0}
          >
            <Play className="size-4" aria-hidden="true" />
            {activeRun ? "Running…" : "Run benchmark"}
          </Button>
        </div>

        {!live && chosen.some((name) => !scenarios.find((s) => s.name === name)?.cached) && (
          <p className="mt-3 text-xs text-warning">
            Some selected scenarios have no cached extraction. Replay runs
            will fail for those — run them once live, or untick them.
          </p>
        )}

        {activeRun && (
          <p className="mt-4 flex items-center gap-2 text-sm text-steel" role="status">
            <span
              aria-hidden="true"
              className="size-1.5 animate-pulse rounded-full bg-signal"
            />
            {activeRun.scenario
              ? `${activeRun.scenario} (${activeRun.index}/${activeRun.total})`
              : "Starting…"}
          </p>
        )}

        {runMutation.isError && (
          <p role="alert" className="mt-3 text-sm text-error">
            {runMutation.error instanceof Error
              ? runMutation.error.message
              : "Could not start the run."}
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-ink">Previous runs</h2>

        {runsQuery.isPending ? (
          <p className="text-sm text-steel">Loading…</p>
        ) : (runsQuery.data?.runs.length ?? 0) === 0 ? (
          <p className="text-sm text-steel">No benchmark runs yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-hairline bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-hairline text-xs text-steel">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Started</th>
                  <th className="px-4 py-2.5 font-medium">Mode</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium">Recall</th>
                  <th className="px-4 py-2.5 font-medium">Retention</th>
                  <th className="px-4 py-2.5 font-medium">Unsupported</th>
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {runsQuery.data?.runs.map((run) => (
                  <RunRow key={run.run_id} run={run} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run live?</DialogTitle>
            <DialogDescription>
              This calls Sarvam once per scenario ({chosen.length}{" "}
              {chosen.length === 1 ? "job" : "jobs"}) and cannot be undone. A
              replay run reuses the cached extraction and costs nothing.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button onClick={() => runMutation.mutate()}>Run live</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function RunRow({ run }: { run: EvalRun }) {
  const [opening, setOpening] = useState(false)
  const totals = useMemo(() => {
    const items = run.scenarios ?? []

    if (items.length === 0) return null

    const mean = (pick: (item: (typeof items)[number]) => number | null | undefined) => {
      const values = items
        .map(pick)
        .filter((value): value is number => typeof value === "number")

      return values.length
        ? values.reduce((total, value) => total + value, 0) / values.length
        : null
    }

    return {
      recall: mean((item) => item.summary.recall),
      retention: mean((item) => item.summary.retention),
      unsupported: mean((item) => item.summary.unsupported_rate),
      seconds: items.reduce(
        (total, item) => total + (item.summary.total_seconds ?? 0),
        0,
      ),
    }
  }, [run.scenarios])

  return (
    <tr>
      <td className="px-4 py-2.5 text-ink">{when(run.started_at)}</td>
      <td className="px-4 py-2.5 text-steel">{run.mode ?? "—"}</td>
      <td className="px-4 py-2.5">
        {run.stale ? (
          <span className="text-warning">interrupted</span>
        ) : run.status === "failed" ? (
          <span className="text-error" title={run.error ?? undefined}>
            failed
          </span>
        ) : (
          <span className="text-steel">{run.status}</span>
        )}
      </td>
      <td className="px-4 py-2.5 text-ink">{percent(totals?.recall)}</td>
      <td className="px-4 py-2.5 text-ink">{percent(totals?.retention)}</td>
      <td className="px-4 py-2.5 text-ink">{percent(totals?.unsupported)}</td>
      <td className="px-4 py-2.5 text-steel">{seconds(totals?.seconds)}</td>
      <td className="px-4 py-2.5 text-right">
        {run.result_available && (
          <Button
            variant="ghost"
            size="xs"
            disabled={opening}
            onClick={() => {
              setOpening(true)
              void openEvalReport(run.run_id).finally(() => setOpening(false))
            }}
          >
            <ExternalLink className="size-3.5" aria-hidden="true" />
            Report
          </Button>
        )}
      </td>
    </tr>
  )
}

type Stat = { value: string; label: string; note?: string }

function statsFor(record: GenerationEvalRecord): Stat[] {
  const s = record.summary
  const stats: Stat[] = []

  if (
    typeof s.functional_retained === "number" &&
    typeof s.functional_input === "number" &&
    s.functional_input > 0
  ) {
    stats.push({
      value: percent(s.functional_retained / s.functional_input),
      label: "requirements kept",
      note: `${s.functional_retained} of ${s.functional_input}`,
    })
  } else if (typeof s.retention === "number") {
    stats.push({ value: percent(s.retention), label: "requirements kept" })
  }

  if (
    typeof s.items_scored === "number" &&
    typeof s.unsupported_items === "number" &&
    s.items_scored > 0
  ) {
    const traced = s.items_scored - s.unsupported_items

    stats.push({
      value: percent(traced / s.items_scored),
      label: "lines traced to sources",
      note:
        s.unsupported_items === 0
          ? "none missing"
          : `${s.unsupported_items} not found`,
    })
  } else if (typeof s.unsupported_rate === "number") {
    stats.push({
      value: percent(1 - s.unsupported_rate),
      label: "lines traced to sources",
    })
  }

  if (typeof s.sections_present === "number") {
    const empty = 11 - s.sections_present

    stats.push({
      value: `${s.sections_present}/11`,
      label: "sections filled",
      note: empty === 0 ? "none empty" : `${empty} empty`,
    })
  }

  if (typeof s.total_seconds === "number") {
    stats.push({
      value: seconds(s.total_seconds),
      label: "generation time",
    })
  }

  return stats
}

function GenerationsTab() {
  const query = useQuery({
    queryKey: ["eval-generations"],
    queryFn: getGenerationEvals,
  })

  if (query.isPending) return <p className="text-sm text-steel">Loading…</p>

  if (query.isError) {
    return (
      <p role="alert" className="text-sm text-error">
        Could not load generation records.
      </p>
    )
  }

  const records = query.data.records

  if (records.length === 0) {
    return (
      <p className="text-sm text-steel">
        No generations scored yet. Generate a BRD and it appears here.
      </p>
    )
  }

  const [latest, ...older] = records

  return (
    <div className="space-y-6">
      <LatestGeneration record={latest} />

      {older.length > 0 && <HistoryTable records={older} />}

      <p className="text-xs leading-5 text-steel">
        <span className="text-ink">Requirements kept</span> — of everything
        extracted from your sources, how much survived into the document.{" "}
        <span className="text-ink">Lines traced</span> — how much of the BRD
        can be found in what you uploaded.{" "}
        <span className="text-ink">Sections</span> — are all eleven parts
        filled. A generation is marked “worth a look” when fewer than 85% of
        requirements are kept, more than 15% of lines cannot be traced, a
        section is empty, or lines repeat. These are quiet conventions, not a
        verdict on the writing.
      </p>
    </div>
  )
}

function LatestGeneration({ record }: { record: GenerationEvalRecord }) {
  const [expanded, setExpanded] = useState(false)

  const recordId = record.record_id
  const stats = statsFor(record)
  const needsLook = record.verdict?.level === "review"

  const detail = useQuery({
    queryKey: ["eval-generation", recordId],
    queryFn: () => getGenerationEval(recordId as string),
    enabled: expanded && Boolean(recordId),
  })

  return (
    <section className="overflow-hidden rounded-xl border border-hairline bg-surface">
      <header className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-hairline px-5 py-3">
        <h2 className="text-sm font-semibold text-ink">Latest generation</h2>

        <p className="flex flex-wrap items-center gap-x-2 text-xs text-steel">
          <span>{when(record.recorded_at)}</span>
          <span aria-hidden="true">·</span>
          <span className="font-mono">
            {record.workspace_id?.slice(0, 8) ?? ""}
          </span>
          <span aria-hidden="true">·</span>
          <span>{needsLook ? "Worth a look" : "Looks complete"}</span>
        </p>
      </header>

      <div
        className={`grid divide-x divide-y divide-hairline ${
          stats.length >= 4
            ? "grid-cols-2 sm:grid-cols-4"
            : "grid-cols-2 sm:grid-cols-3"
        }`}
      >
        {stats.map((stat) => (
          <div key={stat.label} className="px-5 py-5">
            <p className="text-3xl font-semibold leading-none tabular-nums text-ink">
              {stat.value}
            </p>
            <p className="mt-2 text-xs leading-4 text-steel">{stat.label}</p>
            {stat.note && (
              <p className="mt-1 text-xs tabular-nums text-faint">
                {stat.note}
              </p>
            )}
          </div>
        ))}
      </div>

      {needsLook && (record.verdict?.reasons.length ?? 0) > 0 && (
        <ul className="space-y-1 border-t border-hairline px-5 py-3 text-sm text-body">
          {record.verdict?.reasons.map((reason) => (
            <li key={reason}>· {reason}</li>
          ))}
        </ul>
      )}

      <div className="border-t border-hairline px-5 py-3">
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          className="flex items-center gap-1.5 text-sm text-ink hover:underline"
        >
          {expanded ? (
            <ChevronDown className="size-3.5 text-steel" aria-hidden="true" />
          ) : (
            <ChevronRight className="size-3.5 text-steel" aria-hidden="true" />
          )}
          {expanded ? "Hide detail" : "Show what it checked"}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-hairline bg-canvas/40 px-5 py-5">
          {!recordId ? (
            <p className="text-xs text-steel">This record has no id.</p>
          ) : detail.isPending ? (
            <p className="text-xs text-steel">Loading detail…</p>
          ) : detail.isError ? (
            <p className="text-xs text-error">Could not load this record.</p>
          ) : (
            <GenerationDetail detail={detail.data} />
          )}
        </div>
      )}
    </section>
  )
}

function HistoryTable({ records }: { records: GenerationEvalRecord[] }) {
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold text-ink">
        Earlier generations
      </h2>

      <div className="overflow-x-auto rounded-xl border border-hairline bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-hairline text-xs text-steel">
            <tr>
              <th className="px-4 py-2.5 font-medium">Generated</th>
              <th className="px-4 py-2.5 font-medium">Kept</th>
              <th className="px-4 py-2.5 font-medium">Traced</th>
              <th className="px-4 py-2.5 font-medium">Sections</th>
              <th className="px-4 py-2.5 font-medium">Time</th>
              <th className="px-4 py-2.5 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {records.map((record) => {
              const s = record.summary

              return (
                <tr key={record.record_id ?? record.job_id}>
                  <td className="px-4 py-2.5 text-ink">
                    {when(record.recorded_at)}
                    <span className="ml-2 font-mono text-xs text-steel">
                      {record.workspace_id?.slice(0, 8) ?? ""}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-ink">
                    {percent(s.retention)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-ink">
                    {typeof s.unsupported_rate === "number"
                      ? percent(1 - s.unsupported_rate)
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-ink">
                    {s.sections_present ?? "—"}/11
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-steel">
                    {seconds(s.total_seconds)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs text-steel">
                    {s.retention === null || s.retention === undefined
                      ? "not scored"
                      : "scored"}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function GenerationDetail({
  detail,
}: {
  detail: Awaited<ReturnType<typeof getGenerationEval>>
}) {
  const dropped = [
    ...(detail.metrics.retention?.functional?.dropped ?? []),
    ...(detail.metrics.retention?.non_functional?.dropped ?? []),
  ]
  const untraced = detail.metrics.groundedness?.unsupported ?? []
  const duplicates = detail.metrics.duplication?.duplicates ?? []
  const timings = Object.entries(detail.timings ?? {})

  return (
    <div className="space-y-4 text-sm">
      <div>
        <p className="text-xs font-medium text-steel">
          Requirements not kept ({dropped.length})
        </p>
        {dropped.length === 0 ? (
          <p className="mt-1 text-xs text-steel">
            Every requirement we extracted from your sources is represented.
          </p>
        ) : (
          <ul className="mt-1.5 space-y-2">
            {dropped.map((item) => (
              <li key={item.text}>
                <p className="text-ink">{item.text}</p>
                {item.best_match && (
                  <p className="mt-0.5 text-xs text-steel">
                    Closest line in the BRD: “{item.best_match}”
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="text-xs font-medium text-steel">
          Lines not found in your sources ({untraced.length})
        </p>
        {untraced.length === 0 ? (
          <p className="mt-1 text-xs text-steel">
            Every line traces back to your uploaded material.
          </p>
        ) : (
          <ul className="mt-1.5 space-y-2">
            {untraced.slice(0, 5).map((item) => (
              <li key={`${item.section}-${item.text}`}>
                <p className="text-ink">{item.text}</p>
                <p className="mt-0.5 text-xs text-steel">
                  in {item.section.replaceAll("_", " ")} ·{" "}
                  {percent(item.score)} traceable
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="text-xs font-medium text-steel">
          Repeated lines ({duplicates.length})
        </p>
        {duplicates.length === 0 ? (
          <p className="mt-1 text-xs text-steel">Nothing is repeated.</p>
        ) : (
          <ul className="mt-1.5 space-y-2">
            {duplicates.slice(0, 3).map((item) => (
              <li key={item.text}>
                <p className="text-ink">{item.text}</p>
                <p className="mt-0.5 text-xs text-steel">
                  appears {item.count} times in {item.sections.join(", ")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <p className="text-xs font-medium text-steel">Where the time went</p>
        <dl className="mt-1.5 space-y-1 text-xs">
          {timings.map(([phase, value]) => (
            <div key={phase} className="flex justify-between gap-3">
              <dt className="text-steel">{phase.replaceAll("_", " ")}</dt>
              <dd className="tabular-nums text-ink">{seconds(value)}</dd>
            </div>
          ))}
          {detail.usage && (
            <div className="flex justify-between gap-3 border-t border-hairline pt-1">
              <dt className="text-steel">tokens (prompt / thinking)</dt>
              <dd className="tabular-nums text-ink">
                {detail.usage.prompt_tokens ?? "—"} /{" "}
                {detail.usage.thought_tokens ?? "—"}
              </dd>
            </div>
          )}
        </dl>
      </div>
    </div>
  )
}

export default EvalsPage
