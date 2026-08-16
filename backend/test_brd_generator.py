import json
from pathlib import Path

from consolidators.knowledge_consolidator import (
    KnowledgeConsolidator,
)
from extractors.sarvam_knowledge_mapper import (
    SarvamKnowledgeMapper,
)
from generators.brd_generator import BRDGenerator

SARVAM_OUTPUT = Path("output/sarvam_extraction.json")

BRD_SCHEMA = Path("generators/schemas/brd_schema.json")

OUTPUT_PATH = Path("output/generated_brd.json")


def main() -> None:
    sarvam_response = json.loads(SARVAM_OUTPUT.read_text(encoding="utf-8"))

    mapper = SarvamKnowledgeMapper()

    document_knowledge = mapper.map(sarvam_response)

    consolidator = KnowledgeConsolidator()

    project_knowledge = consolidator.consolidate([document_knowledge])

    generator = BRDGenerator(schema_path=BRD_SCHEMA)

    brd = generator.generate(project_knowledge)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            brd,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"BRD generated: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
