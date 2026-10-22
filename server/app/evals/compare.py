"""Compare two benchmark runs side by side.

This exists because "we made it faster" is a claim and a table is
evidence. Both runs must have been produced from the same cached
extraction, otherwise the latency difference includes a Sarvam round trip
that has nothing to do with the change being tested.
"""

from app.evals.report import SUMMARY_FIELDS, _format


def compare_runs(run_a: dict, run_b: dict) -> str:
    label_a = _label(run_a)
    label_b = _label(run_b)

    lines = [
        "# BRD evaluation comparison",
        "",
        f"- **A:** {label_a}",
        f"- **B:** {label_b}",
        "",
    ]

    scenarios_a = {item["scenario"]: item for item in run_a.get("scenarios", [])}
    scenarios_b = {item["scenario"]: item for item in run_b.get("scenarios", [])}

    if run_a.get("mode") != run_b.get("mode"):
        lines += [
            "> Warning: the two runs used different modes "
            f"({run_a.get('mode')} vs {run_b.get('mode')}), so latency "
            "differences include the extraction step.",
            "",
        ]

    for name in sorted(set(scenarios_a) | set(scenarios_b)):
        lines += [f"## {name}", "", "| Metric | A | B | Change |", "|---|---|---|---|"]

        summary_a = scenarios_a.get(name, {}).get("summary_median", {})
        summary_b = scenarios_b.get(name, {}).get("summary_median", {})

        for key, label, direction in SUMMARY_FIELDS:
            value_a = summary_a.get(key)
            value_b = summary_b.get(key)

            lines.append(
                "| {} | {} | {} | {} |".format(
                    label,
                    _format(value_a),
                    _format(value_b),
                    _change(value_a, value_b, direction),
                )
            )

        lines += ["", "**Latency (median, seconds)**", "", "| Stage | A | B | Change |", "|---|---|---|---|"]

        timings_a = scenarios_a.get(name, {}).get("timing_median", {})
        timings_b = scenarios_b.get(name, {}).get("timing_median", {})

        for stage in sorted(set(timings_a) | set(timings_b)):
            value_a = timings_a.get(stage)
            value_b = timings_b.get(stage)

            lines.append(
                "| {} | {} | {} | {} |".format(
                    stage,
                    _format(value_a),
                    _format(value_b),
                    _change(value_a, value_b, "lower"),
                )
            )

        lines.append("")

    return "\n".join(lines)


def _label(run: dict) -> str:
    config = run.get("config", {})

    return "{} (model={}, thinking={}, dedupe={})".format(
        run.get("run_id"),
        config.get("model") or "default",
        config.get("thinking_budget"),
        "on" if config.get("dedupe") else "off",
    )


def _change(value_a: object, value_b: object, direction: str) -> str:
    if not isinstance(value_a, (int, float)) or not isinstance(value_b, (int, float)):
        return "—"

    if value_a == 0:
        return "—"

    change = (value_b - value_a) / abs(value_a) * 100

    # For metrics where lower is better, a negative change is an
    # improvement — say which it is instead of leaving a signed number to
    # be interpreted by the reader.
    improving = change < 0 if direction == "lower" else change > 0

    if abs(change) < 0.5:
        return "no change"

    arrow = "▲" if change > 0 else "▼"

    return f"{arrow} {abs(change):.1f}% {'better' if improving else 'worse'}"
