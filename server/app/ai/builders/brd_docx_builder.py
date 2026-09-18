from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.ai.models.artifacts.brd import BRD


def _add_page_number_footer(document: Document) -> None:
    """
    Centered gray page number in the default footer.
    """
    paragraph = document.sections[0].footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = paragraph.add_run()
    run.font.name = "Arial"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x8E, 0x8E, 0x8E)

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)


class BRDDocxBuilder:
    """
    Builds a human-readable DOCX from a BRD object.
    """

    LEFT_MARGIN = 0.87
    RIGHT_MARGIN = 0.87
    TOP_MARGIN = 0.87
    BOTTOM_MARGIN = 0.87

    BODY_FONT_SIZE = 10
    SECTION_FONT_SIZE = 14
    SUBHEADING_FONT_SIZE = 11
    TITLE_FONT_SIZE = 22
    PROJECT_TITLE_FONT_SIZE = 16

    def build(
        self,
        brd: BRD,
        output_path: str,
    ) -> str:
        document = Document()

        self._configure_document(document)
        self._configure_styles(document)
        _add_page_number_footer(document)

        self._add_title(
            document,
            brd,
        )

        self._add_executive_summary(
            document,
            brd,
        )

        self._add_project_overview(
            document,
            brd,
        )

        self._add_business_objectives(
            document,
            brd,
        )

        self._add_scope(
            document,
            brd,
        )

        self._add_stakeholders(
            document,
            brd,
        )

        self._add_business_requirements(
            document,
            brd,
        )

        self._add_functional_requirements(
            document,
            brd,
        )

        self._add_non_functional_requirements(
            document,
            brd,
        )

        self._add_assumptions_and_constraints(
            document,
            brd,
        )

        self._add_risks_and_decisions(
            document,
            brd,
        )

        self._add_open_questions(
            document,
            brd,
        )

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        document.save(str(output))

        return str(output)

    @staticmethod
    def _configure_document(
        document: Document,
    ) -> None:
        section = document.sections[0]

        section.left_margin = Inches(
            BRDDocxBuilder.LEFT_MARGIN
        )

        section.right_margin = Inches(
            BRDDocxBuilder.RIGHT_MARGIN
        )

        section.top_margin = Inches(
            BRDDocxBuilder.TOP_MARGIN
        )

        section.bottom_margin = Inches(
            BRDDocxBuilder.BOTTOM_MARGIN
        )

    @staticmethod
    def _configure_styles(
        document: Document,
    ) -> None:
        normal_style = document.styles["Normal"]

        normal_style.font.name = "Arial"
        normal_style.font.size = Pt(
            BRDDocxBuilder.BODY_FONT_SIZE
        )

        normal_style.paragraph_format.space_after = Pt(6)
        normal_style.paragraph_format.line_spacing = 1.15

    def _add_title(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        paragraph = document.add_paragraph()

        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

        paragraph.paragraph_format.space_after = Pt(4)

        run = paragraph.add_run(
            "BUSINESS REQUIREMENTS DOCUMENT"
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(
            self.TITLE_FONT_SIZE
        )

        project_paragraph = document.add_paragraph()

        project_paragraph.paragraph_format.space_after = Pt(8)

        project_run = project_paragraph.add_run(
            self._normalize_text(
                brd.project_overview.project_name
            )
        )

        project_run.bold = True
        project_run.font.name = "Arial"
        project_run.font.size = Pt(
            self.PROJECT_TITLE_FONT_SIZE
        )

        separator = document.add_paragraph()

        separator.paragraph_format.space_after = Pt(8)

    def _add_executive_summary(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "1. Executive Summary",
        )

        self._add_paragraph(
            document,
            brd.executive_summary.content,
        )

    def _add_project_overview(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "2. Project Overview",
        )

        self._add_labeled_value(
            document,
            "Project Name",
            brd.project_overview.project_name,
        )

        self._add_labeled_value(
            document,
            "Description",
            brd.project_overview.description,
        )

    def _add_business_objectives(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "3. Business Objectives",
        )

        self._add_bullets(
            document,
            brd.business_objectives.objectives,
        )

    def _add_scope(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "4. Scope",
        )

        self._add_subheading(
            document,
            "In Scope",
        )

        self._add_bullets(
            document,
            brd.scope.in_scope,
        )

        self._add_subheading(
            document,
            "Out of Scope",
        )

        self._add_bullets(
            document,
            brd.scope.out_of_scope,
        )

    def _add_stakeholders(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "5. Stakeholders",
        )

        for stakeholder in brd.stakeholders.stakeholders:
            details = self._normalize_text(
                stakeholder.name
            )

            if stakeholder.role:
                details += (
                    " – "
                    f"{self._normalize_text(stakeholder.role)}"
                )

            if stakeholder.organization:
                details += (
                    f" ("
                    f"{self._normalize_text(stakeholder.organization)}"
                    f")"
                )

            self._add_bullet(
                document,
                details,
            )

    def _add_business_requirements(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "6. Business Requirements",
        )

        self._add_bullets(
            document,
            brd.business_requirements.requirements,
        )

    def _add_functional_requirements(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "7. Functional Requirements",
        )

        self._add_bullets(
            document,
            brd.functional_requirements.requirements,
        )

    def _add_non_functional_requirements(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "8. Non-Functional Requirements",
        )

        self._add_bullets(
            document,
            brd.non_functional_requirements.requirements,
        )

    def _add_assumptions_and_constraints(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "9. Assumptions & Constraints",
        )

        self._add_subheading(
            document,
            "Assumptions",
        )

        self._add_bullets(
            document,
            brd.assumptions_and_constraints.assumptions,
        )

        self._add_subheading(
            document,
            "Constraints",
        )

        self._add_bullets(
            document,
            brd.assumptions_and_constraints.constraints,
        )

    def _add_risks_and_decisions(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "10. Risks & Decisions",
        )

        self._add_subheading(
            document,
            "Risks",
        )

        self._add_bullets(
            document,
            brd.risks_and_decisions.risks,
        )

        self._add_subheading(
            document,
            "Decisions",
        )

        self._add_bullets(
            document,
            brd.risks_and_decisions.decisions,
        )

    def _add_open_questions(
        self,
        document: Document,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            document,
            "11. Open Questions",
        )

        self._add_bullets(
            document,
            brd.open_questions.questions,
        )

    @staticmethod
    def _add_section_heading(
        document: Document,
        text: str,
    ) -> None:
        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_before = Pt(10)
        paragraph.paragraph_format.space_after = Pt(4)

        run = paragraph.add_run(
            BRDDocxBuilder._normalize_text(text)
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(
            BRDDocxBuilder.SECTION_FONT_SIZE
        )


    @staticmethod
    def _add_subheading(
        document: Document,
        text: str,
    ) -> None:
        paragraph = document.add_paragraph()

        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(2)

        run = paragraph.add_run(
            BRDDocxBuilder._normalize_text(text)
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(
            BRDDocxBuilder.SUBHEADING_FONT_SIZE
        )

    @staticmethod
    def _add_paragraph(
        document: Document,
        text: str,
    ) -> None:
        paragraph = document.add_paragraph()

        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15

        run = paragraph.add_run(
            BRDDocxBuilder._normalize_text(text)
        )

        run.font.name = "Arial"
        run.font.size = Pt(
            BRDDocxBuilder.BODY_FONT_SIZE
        )

    @staticmethod
    def _add_labeled_value(
        document: Document,
        label: str,
        value: str,
    ) -> None:
        paragraph = document.add_paragraph()

        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15

        label_run = paragraph.add_run(
            f"{BRDDocxBuilder._normalize_text(label)}: "
        )

        label_run.bold = True
        label_run.font.name = "Arial"
        label_run.font.size = Pt(
            BRDDocxBuilder.BODY_FONT_SIZE
        )

        value_run = paragraph.add_run(
            BRDDocxBuilder._normalize_text(value)
        )

        value_run.font.name = "Arial"
        value_run.font.size = Pt(
            BRDDocxBuilder.BODY_FONT_SIZE
        )

    @staticmethod
    def _add_bullet(
        document: Document,
        text: str,
    ) -> None:
        paragraph = document.add_paragraph(
            style="List Bullet"
        )

        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.line_spacing = 1.15

        run = paragraph.add_run(
            BRDDocxBuilder._normalize_text(text)
        )

        run.font.name = "Arial"
        run.font.size = Pt(
            BRDDocxBuilder.BODY_FONT_SIZE
        )

    @staticmethod
    def _add_bullets(
        document: Document,
        items: list[str],
    ) -> None:
        if not items:
            paragraph = document.add_paragraph()

            paragraph.paragraph_format.space_after = Pt(3)

            run = paragraph.add_run(
                "None specified."
            )

            run.italic = True
            run.font.name = "Arial"
            run.font.size = Pt(
                BRDDocxBuilder.BODY_FONT_SIZE
            )

            return

        for item in items:
            BRDDocxBuilder._add_bullet(
                document,
                item,
            )

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """
        Converts common Unicode punctuation generated by the LLM
        into characters supported consistently by the document fonts.
        """

        # NOTE: Arial carries the full Unicode range, so en-dashes and
        # bullets pass through untouched (unlike the PDF's latin-1 font).
        replacements = {
            "—": "--",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "…": "...",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text
