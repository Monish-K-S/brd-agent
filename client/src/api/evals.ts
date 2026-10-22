import { apiClient } from "./client";

export type EvalScenarioSummary = {
  name: string;
  level: string;
  facts: number;
  documents: number;
  chars: number;
  cached: boolean;
};

export type EvalMetricSummary = {
  recall?: number | null;
  retention?: number | null;
  unsupported_rate?: number | null;
  duplicate_items?: number | null;
  sections_present?: number | null;
  total_seconds?: number | null;
  valid?: boolean | null;
};

export type EvalRun = {
  run_id: string;
  status: "running" | "completed" | "failed";
  mode: "live" | "replay" | null;
  index?: number;
  total?: number;
  scenario?: string | null;
  error?: string | null;
  started_at?: string | null;
  result_available: boolean;
  stale: boolean;
  scenarios?: {
    scenario: string;
    summary: EvalMetricSummary;
    timings: Record<string, number>;
  }[];
};

export type GenerationEvalSummary = EvalMetricSummary & {
  functional_input?: number | null;
  functional_retained?: number | null;
  unsupported_items?: number | null;
  items_scored?: number | null;
};

export type GenerationVerdict = {
  level: "complete" | "review";
  reasons: string[];
};

export type GenerationEvalRecord = {
  record_id: string | null;
  job_id: string | null;
  workspace_id: string | null;
  recorded_at: string | null;
  summary: GenerationEvalSummary;
  usage: { prompt_tokens?: number | null; thought_tokens?: number | null } | null;
  verdict?: GenerationVerdict;
};

export type GenerationEvalDetail = GenerationEvalRecord & {
  timings: Record<string, number>;
  metrics: {
    retention?: {
      functional?: { input: number; retained: number; dropped: DroppedRequirement[] };
      non_functional?: { input: number; retained: number; dropped: DroppedRequirement[] };
    };
    groundedness?: {
      unsupported?: { section: string; text: string; score: number }[];
    };
    duplication?: {
      duplicates?: { text: string; count: number; sections: string[] }[];
    };
  };
};

export type DroppedRequirement = {
  text: string;
  score: number;
  best_match: string | null;
};

export type EvalScenariosResponse = {
  scenarios: EvalScenarioSummary[];
  active_run: { run_id: string; started_at: number } | null;
};

export type EvalRunsResponse = {
  count: number;
  runs: EvalRun[];
  active_run: { run_id: string; started_at: number } | null;
};

export async function getEvalScenarios(): Promise<EvalScenariosResponse> {
  const response = await apiClient.get<EvalScenariosResponse>("/evals/scenarios");

  return response.data;
}

export async function getEvalRuns(): Promise<EvalRunsResponse> {
  const response = await apiClient.get<EvalRunsResponse>("/evals/runs");

  return response.data;
}

export async function startEvalRun(
  scenarios: string[],
  replay: boolean,
): Promise<{ run_id: string; status: string; mode: string }> {
  const response = await apiClient.post<{
    run_id: string;
    status: string;
    mode: string;
  }>("/evals/run", { scenarios, replay });

  return response.data;
}

export async function getGenerationEval(
  recordId: string,
): Promise<GenerationEvalDetail> {
  const response = await apiClient.get<GenerationEvalDetail>(
    `/evals/generations/${recordId}`,
  );

  return response.data;
}

export async function getGenerationEvals(): Promise<{
  count: number;
  records: GenerationEvalRecord[];
}> {
  const response = await apiClient.get<{
    count: number;
    records: GenerationEvalRecord[];
  }>("/evals/generations");

  return response.data;
}

/**
 * Open a run's report.
 *
 * The report route requires the same Bearer token as every other request,
 * so a plain `window.open` would 401. Fetch it through the authenticated
 * client and hand the browser a blob instead.
 */
export async function openEvalReport(runId: string): Promise<void> {
  const response = await apiClient.get<string>(
    `/evals/runs/${runId}/report.html`,
    { responseType: "text", transformResponse: (data) => data },
  );

  const blob = new Blob([response.data], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const opened = window.open(url, "_blank", "noopener,noreferrer");

  if (!opened) URL.revokeObjectURL(url);
}
