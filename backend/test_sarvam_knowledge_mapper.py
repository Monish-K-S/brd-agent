import json
from pathlib import Path

from extractors.sarvam_knowledge_mapper import (
    SarvamKnowledgeMapper,
)


INPUT_PATH = Path(
    "output/sarvam_extraction.json"
)


def main() -> None:
    response = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    mapper = SarvamKnowledgeMapper()

    knowledge = mapper.map(response)

    print(knowledge)


if __name__ == "__main__":
    main()
