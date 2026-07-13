from uuid import uuid4

from llm.response_parser import ResponseParser


def main():
    response = {
        "functional_requirements": [
            {
                "description": "The system should allow users to upload project documents."
            },
            {
                "description": "The generated BRD should include all business requirements."
            },
        ],
        "non_functional_requirements": [],
    }

    parser = ResponseParser()

    result = parser.parse(
        response=response,
        source_chunk_ids=[
            uuid4(),
            uuid4(),
        ],
    )

    print(result)


if __name__ == "__main__":
    main()
