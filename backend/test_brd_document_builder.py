import json
from pathlib import Path

from generators.brd_mapper import BRDMapper
from builders.brd_document_builder import BRDDocumentBuilder


INPUT_PATH = Path(
    "output/generated_brd.json"
)

OUTPUT_PATH = Path(
    "output/customer_support_portal_brd.pdf"
)


def main() -> None:
    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    mapper = BRDMapper()

    brd = mapper.map(data)

    builder = BRDDocumentBuilder()

    output = builder.build(
        brd=brd,
        output_path=str(OUTPUT_PATH),
    )

    print(
        f"BRD PDF generated: {Path(output).resolve()}"
    )


if __name__ == "__main__":
    main()
