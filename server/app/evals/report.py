"""Render benchmark results as JSON, Markdown and a standalone page.

The HTML is deliberately dependency-free: inline CSS, CSS-only bars, no
JavaScript and no CDN. It has to open from disk on a laptop with the
network off, and it has to still look the same in a year — an artefact
that needs npm to render is not an artefact.
"""

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

SCHEMA_VERSION = 1

# Order matters: this is how the numbers are presented.
SUMMARY_FIELDS = (
    ("recall", "Fact recall", "higher"),
    ("retention", "Requirement retention", "higher"),
    ("unsupported_rate", "Unsupported items", "lower"),
    ("duplicate_items", "Duplicate items", "lower"),
    ("sections_present", "Sections filled", "higher"),
    ("total_seconds", "Total seconds", "lower"),
)


def build_run(
    run_id: str,
    results: list[dict],
    *,
    mode: str,
    config: dict,
    started_at: str | None = None,
) -> dict:
    """Assemble one run's results, aggregating repeats per scenario."""
    scenarios: dict[str, list[dict]] = {}

    for result in results:
        scenarios.setdefault(result["scenario"], []).append(result)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at or _now(),
        "finished_at": _now(),
        "mode": mode,
        "config": config,
        "scenarios": [
            {
                "scenario": name,
                "repeats": repeats,
                "summary_median": _median_summary(repeats),
                "timing_median": _median_timings(repeats),
            }
            for name, repeats in scenarios.items()
        ],
    }


def write_run(run: dict, out_dir: str | Path) -> Path:
    """Write results.json, report.md and report.html. Returns the directory."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "results.json").write_text(
        json.dumps(run, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (directory / "report.md").write_text(render_markdown(run), encoding="utf-8")

    (directory / "report.html").write_text(render_html(run), encoding="utf-8")

    return directory


# ------------------------------------------------------------- markdown


def render_markdown(run: dict) -> str:
    lines = [
        f"# BRD evaluation — {run['run_id']}",
        "",
        f"- **Mode:** {run['mode']}",
        f"- **Started:** {run['started_at']}",
        f"- **Model:** {run['config'].get('model') or 'default'}",
        f"- **Thinking budget:** {run['config'].get('thinking_budget')}",
        f"- **Dedupe:** {'on' if run['config'].get('dedupe') else 'off'}",
        f"- **Repeats:** {run['config'].get('repeats')}",
        "",
    ]

    for scenario in run["scenarios"]:
        summary = scenario["summary_median"]

        lines += [
            f"## {scenario['scenario']}",
            "",
            "| Metric | Value |",
            "|---|---|",
        ]

        for key, label, _ in SUMMARY_FIELDS:
            lines.append(f"| {label} | {_format(summary.get(key))} |")

        lines += ["", "**Latency (median, seconds)**", "", "| Stage | Seconds |", "|---|---|"]

        for stage, seconds in scenario["timing_median"].items():
            lines.append(f"| {stage} | {_format(seconds)} |")

        missed = _missed_facts(scenario)

        if missed:
            lines += ["", "**Missed facts**", ""]

            for fact in missed:
                lines.append(f"- `{fact['id']}` {fact['text']}")

        lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------- html

_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 48px 32px 80px;
  background: #F5F1E8; color: #151515;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.55;
}
main { max-width: 920px; margin: 0 auto; }
h1 { font-size: 30px; margin: 0 0 6px; letter-spacing: -0.02em; }
h2 { font-size: 20px; margin: 44px 0 4px; letter-spacing: -0.01em; }
.sub { color: #6D6A63; font-size: 14px; margin: 0 0 28px; }
.meta {
  display: flex; flex-wrap: wrap; gap: 8px 20px;
  padding: 16px 20px; background: #FFFDF8;
  border: 1px solid #DDD8CD; border-radius: 10px;
  font-size: 13px; color: #4A463D; margin-bottom: 8px;
}
.meta b { color: #151515; font-weight: 600; }
table { width: 100%; border-collapse: collapse; margin: 12px 0 8px; font-size: 14px; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid #E7E1D5; }
th { color: #6D6A63; font-weight: 600; font-size: 12px; text-transform: none; }
td.num { font-variant-numeric: tabular-nums; }
.bar { height: 6px; background: #E7E1D5; border-radius: 3px; overflow: hidden; min-width: 90px; }
.bar span { display: block; height: 100%; background: #151515; }
.bar.warn span { background: #B42318; }
.missed { font-size: 13px; color: #4A463D; margin: 10px 0 0; }
.missed code { background: #EEEAE1; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
footer { margin-top: 56px; font-size: 12px; color: #85817A; }
"""


def render_html(run: dict) -> str:
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>BRD evaluation — {html.escape(run['run_id'])}</title>",
        f"<style>{_STYLE}</style>",
        "</head><body><main>",
        "<h1>BRD evaluation</h1>",
        f'<p class="sub">Run {html.escape(run["run_id"])} · {html.escape(run["started_at"])}</p>',
        '<div class="meta">',
        f"<span>Mode <b>{html.escape(str(run['mode']))}</b></span>",
        f"<span>Model <b>{html.escape(str(run['config'].get('model') or 'default'))}</b></span>",
        f"<span>Thinking <b>{html.escape(str(run['config'].get('thinking_budget')))}</b></span>",
        f"<span>Dedupe <b>{'on' if run['config'].get('dedupe') else 'off'}</b></span>",
        f"<span>Repeats <b>{html.escape(str(run['config'].get('repeats')))}</b></span>",
        "</div>",
    ]

    for scenario in run["scenarios"]:
        parts.append(f"<h2>{html.escape(scenario['scenario'])}</h2>")
        parts.append(_html_metrics(scenario["summary_median"]))
        parts.append(_html_latency(scenario["timing_median"]))
        parts.append(_html_missed(scenario))

    parts += [
        "<footer>Generated by the Sourcify evaluation harness. "
        "Fact recall needs a hand-written answer key; retention and "
        "groundedness are computed against the extracted knowledge.</footer>",
        "</main></body></html>",
    ]

    return "\n".join(parts)


def _html_metrics(summary: dict) -> str:
    rows = []

    for key, label, direction in SUMMARY_FIELDS:
        value = summary.get(key)

        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f'<td class="num">{html.escape(_format(value))}</td>'
            f"<td>{_bar(key, value, direction)}</td>"
            "</tr>"
        )

    return (
        "<table><thead><tr><th>Metric</th><th>Value</th><th></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _bar(key: str, value: object, direction: str) -> str:
    """CSS-only bar. Only percentages have a meaningful 0–1 scale."""
    if not isinstance(value, (int, float)) or value is None:
        return ""

    if key in {"duplicate_items", "sections_present", "total_seconds"}:
        return ""

    width = max(0.0, min(1.0, float(value))) * 100

    warn = direction == "lower" and width > 20

    return (
        f'<div class="bar{" warn" if warn else ""}">'
        f'<span style="width:{width:.1f}%"></span></div>'
    )


def _html_latency(timings: dict) -> str:
    if not timings:
        return ""

    largest = max(float(value) for value in timings.values()) or 1.0

    rows = []

    for stage, seconds in timings.items():
        width = float(seconds) / largest * 100

        rows.append(
            "<tr>"
            f"<td>{html.escape(stage)}</td>"
            f'<td class="num">{html.escape(_format(seconds))}</td>'
            f'<td><div class="bar"><span style="width:{width:.1f}%"></span></div></td>'
            "</tr>"
        )

    return (
        "<table><thead><tr><th>Stage</th><th>Seconds</th><th></th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _html_missed(scenario: dict) -> str:
    missed = _missed_facts(scenario)

    if not missed:
        return ""

    items = "".join(
        f"<li><code>{html.escape(str(fact['id']))}</code> "
        f"{html.escape(str(fact['text']))}</li>"
        for fact in missed
    )

    return f'<ul class="missed">{items}</ul>'


# ---------------------------------------------------------------- shared


def _median_summary(repeats: list[dict]) -> dict:
    summaries = [repeat.get("summary", {}) for repeat in repeats]

    keys = {key for summary in summaries for key in summary}

    medians = {}

    for key in sorted(keys):
        values = [summary.get(key) for summary in summaries]

        numbers = [
            value
            for value in values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

        # A boolean (``valid``) or a string has no median. Taking the
        # first repeat is the honest reduction: a median of True/False
        # would be 0.5 and a median of True/True would silently become
        # null, which is how ``valid`` first showed up blank.
        medians[key] = (
            round(median(numbers), 3) if numbers else (values[0] if values else None)
        )

    return medians


def _median_timings(repeats: list[dict]) -> dict:
    timings = [repeat.get("timings", {}) for repeat in repeats]

    keys = {key for timing in timings for key in timing}

    return {
        key: _median_of([timing.get(key) for timing in timings])
        for key in sorted(keys)
    }


def _median_of(values: list) -> float | int | None:
    numbers = [
        value
        for value in values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]

    if not numbers:
        return None

    return round(median(numbers), 3)


def _missed_facts(scenario: dict) -> list[dict]:
    """Missed facts from the first repeat that has a coverage result.

    Coverage is identical across repeats unless the model genuinely
    varies, and when it does the first repeat is the honest thing to
    show rather than an average of two different fact lists.
    """
    for repeat in scenario.get("repeats", []):
        coverage = repeat.get("metrics", {}).get("coverage", {})

        if coverage.get("missed"):
            return coverage["missed"]

    return []


def _format(value: object) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")

    return str(value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
