import json
from pathlib import Path
from pprint import pprint
from generators.brd_mapper import BRDMapper


INPUT_PATH = Path(
    "output/generated_brd.json"
)


def main() -> None:
    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    mapper = BRDMapper()

    brd = mapper.map(data)

    print(brd)


if __name__ == "__main__":
    main()
