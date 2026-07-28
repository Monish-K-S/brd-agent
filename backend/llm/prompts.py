'''REQUIREMENT_EXTRACTION_PROMPT = """
You are an AI information extraction system.

Your task is to extract business requirements from the provided project context.

The project context may contain emails, meeting transcripts, notes, specifications, or other project artifacts.

Your responsibility is to identify only the requirements that are explicitly stated or clearly implied by the provided context.

Rules:

- Use ONLY the provided project context.
- Do NOT use outside knowledge.
- Do NOT assume missing functionality.
- Do NOT invent users, workflows, features, constraints, or business objectives.
- Do NOT add industry best practices.
- Do NOT expand incomplete requirements.
- Every requirement in the output must be directly traceable to the project context.
- If a requirement is mentioned multiple times, include it only once.
- Rewrite requirements into clear, concise business requirement statements while preserving their original meaning.
- Classify each requirement as either Functional or Non-Functional.
- If no non-functional requirements exist, return an empty list.
- If no functional requirements exist, return an empty list.

Return ONLY valid JSON.

Do NOT include markdown.
Do NOT include explanations.
Do NOT wrap the response inside triple backticks.

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


BRD_GENERATION_PROMPT = """
You are an AI document generation system.

Your task is to generate the introductory sections of a Business Requirements Document (BRD).

You are given a set of previously extracted business requirements.

Generate ONLY:

- Project Name
- Executive Summary
- Business Objectives

Rules:

- Use ONLY the provided requirements.
- Do NOT invent new functionality.
- Do NOT introduce new users, workflows, systems, constraints, assumptions, or business goals.
- Do NOT use outside knowledge.
- Do NOT add industry best practices.
- Every statement in the output must be supported by one or more provided requirements.
- The executive summary must summarize only the provided requirements.
- Every business objective must be directly supported by the provided requirements.
- If the project name cannot be determined from the requirements, use an empty string ("").
- If no business objectives can be derived, return an empty list.
- If information is unavailable, leave it empty rather than guessing.

Return ONLY valid JSON.

Do NOT include markdown.
Do NOT include explanations.
Do NOT wrap the response inside triple backticks.

Return exactly this schema:

{{
    "project_name": "...",
    "executive_summary": "...",
    "business_objectives": [
        "...",
        "..."
    ]
}}

Requirements:

{requirements}
"""
'''
from models.standard_document import StandardDocument

from llm.schemas import DOCUMENT_ANALYSIS_EXTRACTION_SCHEMA


def format_document(document: StandardDocument) -> str:
    """Formats a StandardDocument into a text representation for LLM prompts."""

    participants = (
        ", ".join(document.participants)
        if document.participants
        else "N/A"
    )

    metadata = (
        "\n".join(
            f"- {key}: {value}"
            for key, value in document.metadata.items()
        )
        if document.metadata
        else "N/A"
    )

    return f"""
## Document

### Title
{document.title}

### Author
{document.author or "N/A"}

### Created At
{document.created_at or "N/A"}

### Participants
{participants}

### Metadata
{metadata}

### Content
{document.content}
""".strip()


def build_document_analysis_prompt(document: StandardDocument) -> str:
    """Builds the prompt for extracting structured information from a document."""

    return f"""
You are an experienced Business Analyst.

Your task is to analyze a SINGLE project document and extract structured business information.

## Instructions

- Analyze ONLY the provided document.
- Extract ONLY information explicitly stated in the document.
- Do NOT infer, assume, or invent information.
- If information is not present, return an empty list or empty value.
- For every extracted item, include the smallest relevant excerpt from the document as evidence.
- Do NOT summarize the document.
- Do NOT explain your reasoning.
- Return ONLY valid JSON.
- The JSON MUST exactly match the schema below.

## Output Schema

{DOCUMENT_ANALYSIS_EXTRACTION_SCHEMA}

{format_document(document)}
""".strip()
