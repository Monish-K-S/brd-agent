import json
from pathlib import Path

from extractors.sarvam_knowledge_mapper import SarvamKnowledgeMapper
from consolidators.knowledge_consolidator import KnowledgeConsolidator


INPUT_PATH = Path("output/sarvam_extraction.json")


def main() -> None:
    response = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    mapper = SarvamKnowledgeMapper()

    document_knowledge = mapper.map(
        response
    )

    consolidator = KnowledgeConsolidator()

    project_knowledge = consolidator.consolidate(
        [document_knowledge]
    )

    print(project_knowledge)


if __name__ == "__main__":
    main()
