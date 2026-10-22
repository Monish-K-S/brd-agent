"""Benchmark CLI.

    python -m app.evals.run --list
    python -m app.evals.run --scenario smoke
    python -m app.evals.run --scenario all --repeats 2
    python -m app.evals.run --scenario all --repeats 3 --replay
    python -m app.evals.run --compare a/results.json b/results.json

Run from ``server/``: ``SarvamExtractor`` and ``GeminiBRDGenerator`` call
``load_dotenv()``, which finds ``server/.env`` from the working directory.

Exit codes: 0 success, 1 a scenario failed to run, 2 bad usage or a
malformed dataset.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.evals.compare import compare_runs
from app.evals.datasets import (
    ScenarioError,
    load_scenario,
    ordered_scenarios,
)
from app.evals.report import build_run, write_run
from app.evals.runner import (
    MODE_LIVE,
    MODE_REPLAY,
    RunConfig,
    ScenarioRunError,
    run_scenario,
)

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.evals.run",
        description="Run the BRD pipeline against benchmark scenarios.",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="List available scenarios and exit (no API calls).",
    )
    parser.add_argument(
        "--scenario",
        nargs="+",
        default=["all"],
        help="Scenario name(s), or 'all' (default: all).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Runs per scenario (default: 1). Repeats are what make a "
        "latency median meaningful.",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Reuse the cached extraction instead of calling Sarvam. "
        "Fails if a scenario has no cache.",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=None,
        help="Override gemini_thinking_budget for this run.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the generator model for this run.",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Skip consolidator deduplication (for the dedup A/B only).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help=f"Output directory (default: {REPORTS_DIR}/<run id>).",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("A", "B"),
        default=None,
        help="Compare two results.json files and print a Markdown table.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.compare:
        return _compare(*args.compare)

    if args.list_only:
        return _list()

    return _run(args)


def _list() -> int:
    scenarios = ordered_scenarios()

    if not scenarios:
        print("No scenarios found.", file=sys.stderr)

        return 2

    for scenario in scenarios:
        name = scenario.name

        print(
            f"{scenario.level:7} {name:20} {len(scenario.facts):3} facts  "
            f"{len(scenario.inputs)} document(s)  "
            f"{scenario.total_chars} chars"
        )

    return 0


def _compare(path_a: str, path_b: str) -> int:
    import json

    try:
        run_a = json.loads(Path(path_a).read_text(encoding="utf-8"))
        run_b = json.loads(Path(path_b).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read results: {exc}", file=sys.stderr)

        return 2

    print(compare_runs(run_a, run_b))

    return 0


def _run(args) -> int:
    try:
        requested = args.scenario

        if "all" in requested:
            scenario_names = [item.name for item in ordered_scenarios()]
        else:
            scenario_names = requested

        scenarios = [load_scenario(name) for name in scenario_names]
    except ScenarioError as exc:
        print(f"Scenario error: {exc}", file=sys.stderr)

        return 2

    if not scenarios:
        print("No scenarios to run.", file=sys.stderr)

        return 2

    if args.repeats < 1:
        print("--repeats must be at least 1.", file=sys.stderr)

        return 2

    config = RunConfig(
        mode=MODE_REPLAY if args.replay else MODE_LIVE,
        thinking_budget=args.thinking_budget,
        model=args.model,
        dedupe=not args.no_dedupe,
    )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    print(
        f"Run {run_id}: {len(scenarios)} scenario(s) x {args.repeats} "
        f"repeat(s), mode={config.mode}"
    )

    results = []

    for scenario in scenarios:
        for attempt in range(1, args.repeats + 1):
            label = f"{scenario.name} [{attempt}/{args.repeats}]"

            print(f"  {label} ... ", end="", flush=True)

            try:
                result = run_scenario(scenario, config)
            except ScenarioRunError as exc:
                print("FAILED")

                print(f"    {exc}", file=sys.stderr)

                return 1
            except Exception as exc:  # provider/auth failures
                print("FAILED")

                print(
                    f"    {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )

                return 1

            results.append(result.to_dict())

            summary = result.summary

            print(
                "recall={recall} retention={retention} "
                "unsupported={unsupported_rate} {total_seconds}s".format(
                    recall=summary.get("recall"),
                    retention=summary.get("retention"),
                    unsupported_rate=summary.get("unsupported_rate"),
                    total_seconds=summary.get("total_seconds"),
                )
            )

    run = build_run(
        run_id,
        results,
        mode=config.mode,
        config={
            "model": config.model,
            "thinking_budget": config.thinking_budget,
            "dedupe": config.dedupe,
            "repeats": args.repeats,
        },
    )

    out_dir = Path(args.out) if args.out else REPORTS_DIR / run_id

    write_run(run, out_dir)

    print(f"\nWrote {out_dir}/report.html")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
