REQUIREMENT_EXTRACTION_PROMPT = """
You are an experienced Business Analyst.

Your task is to analyze the provided project context and extract business requirements.

Return ONLY valid JSON.

Do not include markdown.

Do not wrap the JSON inside triple backticks.

Return exactly this schema:

{{
  "functional_requirements": [
    {{
      "description": "..."
    }}
  ],
  "non_functional_requirements": [
    {{
      "description": "..."
    }}
  ]
}}

Project Context:

{context}
"""
