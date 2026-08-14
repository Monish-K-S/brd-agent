import json

DOCUMENT_ANALYSIS_EXTRACTION_SCHEMA = json.dumps(
    {
        "project_information": {
            "name": ""
        },
        "stakeholders": [
            {
                "name": "",
                "role": "",
                "evidence": ""
            }
        ],
        "business_objectives": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "functional_requirements": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "non_functional_requirements": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "constraints": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "assumptions": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "decisions": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "risks": [
            {
                "description": "",
                "evidence": ""
            }
        ],
        "open_questions": [
            {
                "description": "",
                "evidence": ""
            }
        ]
    },
    indent=2
)
