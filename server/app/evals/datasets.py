"""Load and validate benchmark scenarios.

A scenario is a directory holding source documents and the ground truth
for them. Validation happens at load time, before any API budget is
spent, because the failure mode this guards against is expensive: a
malformed fact discovered after a live run means paying for that run
twice.

Documents are ``.txt`` on purpose — ``ParserFactory`` accepts only
``.txt``/``.pdf``/``.docx``, so a ``.md`` fixture would either fail or
bypass the real parsing path and quietly measure something else.
"""

import json
from dataclasses import dataclass
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

SUPPORTED_SUFFIXES = {".txt", ".pdf", ".docx"}


class ScenarioError(ValueError):
    """A scenario is missing or malformed."""


@dataclass(frozen=True)
class Scenario:
    name: str
    directory: Path
    expected: dict

    @property
    def inputs(self) -> list[Path]:
        return _source_files(self.directory)

    @property
    def facts(self) -> list[dict]:
        return self.expected.get("facts", [])

    @property
    def total_chars(self) -> int:
        return sum(
            len(path.read_text(encoding="utf-8", errors="replace"))
            for path in self.inputs
            if path.suffix.lower() == ".txt"
        )


def list_scenarios(datasets_dir: str | Path | None = None) -> list[str]:
    base = Path(datasets_dir) if datasets_dir is not None else DATASETS_DIR

    if not base.is_dir():
        return []

    return sorted(
        path.name
        for path in base.iterdir()
        if path.is_dir() and (path / "expected.json").is_file()
    )


def load_scenario(
    name: str,
    datasets_dir: str | Path | None = None,
) -> Scenario:
    base = Path(datasets_dir) if datasets_dir is not None else DATASETS_DIR

    directory = base / name

    if not directory.is_dir():
        raise ScenarioError(f"Unknown scenario: {name}")

    expected_path = directory / "expected.json"

    if not expected_path.is_file():
        raise ScenarioError(f"{name}: missing expected.json")

    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{name}: expected.json is not valid JSON ({exc})") from exc

    _validate(name, directory, expected)

    return Scenario(name=name, directory=directory, expected=expected)


def load_all(datasets_dir: str | Path | None = None) -> list[Scenario]:
    return [
        load_scenario(name, datasets_dir)
        for name in list_scenarios(datasets_dir)
    ]


def _source_files(directory: Path) -> list[Path]:
    """Source documents live in ``inputs/`` so expected.json can sit beside them."""
    inputs = directory / "inputs"

    base = inputs if inputs.is_dir() else directory

    return sorted(
        path
        for path in base.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _validate(name: str, directory: Path, expected: object) -> None:
    if not isinstance(expected, dict):
        raise ScenarioError(f"{name}: expected.json must be an object")

    facts = expected.get("facts")

    if not isinstance(facts, list) or not facts:
        raise ScenarioError(f"{name}: expected.json must list at least one fact")

    inputs = _source_files(directory)

    if not inputs:
        raise ScenarioError(
            f"{name}: no source documents (.txt/.pdf/.docx) in "
            f"{directory / 'inputs'}"
        )

    seen: set[str] = set()

    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ScenarioError(f"{name}: fact #{index} must be an object")

        fact_id = fact.get("id")

        if not isinstance(fact_id, str) or not fact_id.strip():
            raise ScenarioError(f"{name}: fact #{index} needs a non-empty id")

        if fact_id in seen:
            raise ScenarioError(f"{name}: duplicate fact id {fact_id!r}")

        seen.add(fact_id)

        groups = fact.get("groups")

        if not isinstance(groups, list) or not groups:
            raise ScenarioError(
                f"{name}: fact {fact_id!r} needs at least one group of phrasings"
            )

        for group in groups:
            if not isinstance(group, list) or not group:
                raise ScenarioError(
                    f"{name}: fact {fact_id!r} has an empty phrasing group"
                )

            if not all(
                isinstance(alternative, str) and alternative.strip()
                for alternative in group
            ):
                raise ScenarioError(
                    f"{name}: fact {fact_id!r} has a non-string phrasing"
                )
