from pathlib import Path

from fpdf import FPDF

from app.ai.models.artifacts.brd import BRD


class _BRDFolioPDF(FPDF):
    """
    FPDF with a quiet centered page number on every page.
    """

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(
            "Helvetica",
            "",
            9,
        )
        self.set_text_color(140, 140, 140)
        self.cell(
            0,
            10,
            f"{self.page_no()}",
            align="C",
        )
        self.set_text_color(0, 0, 0)


class BRDDocumentBuilder:
    """
    Builds a human-readable PDF from a BRD object.
    """

    LEFT_MARGIN = 22
    RIGHT_MARGIN = 22
    TOP_MARGIN = 22
    BOTTOM_MARGIN = 22

    BODY_FONT_SIZE = 10
    BODY_LINE_HEIGHT = 6.2

    SECTION_FONT_SIZE = 14
    SECTION_LINE_HEIGHT = 8

    SUBHEADING_FONT_SIZE = 11
    SUBHEADING_LINE_HEIGHT = 6

    TITLE_FONT_SIZE = 22
    PROJECT_TITLE_FONT_SIZE = 16

    def build(
        self,
        brd: BRD,
        output_path: str,
    ) -> str:
        pdf = _BRDFolioPDF()

        pdf.set_margins(
            left=self.LEFT_MARGIN,
            top=self.TOP_MARGIN,
            right=self.RIGHT_MARGIN,
        )

        pdf.set_auto_page_break(
            auto=True,
            margin=self.BOTTOM_MARGIN,
        )

        content_width = (
            pdf.w
            - self.LEFT_MARGIN
            - self.RIGHT_MARGIN
        )

        self._add_title(
            pdf,
            content_width,
            brd,
        )

        self._add_executive_summary(
            pdf,
            content_width,
            brd,
        )

        self._add_project_overview(
            pdf,
            content_width,
            brd,
        )

        self._add_business_objectives(
            pdf,
            content_width,
            brd,
        )

        self._add_scope(
            pdf,
            content_width,
            brd,
        )

        self._add_stakeholders(
            pdf,
            content_width,
            brd,
        )

        self._add_business_requirements(
            pdf,
            content_width,
            brd,
        )

        self._add_functional_requirements(
            pdf,
            content_width,
            brd,
        )

        self._add_non_functional_requirements(
            pdf,
            content_width,
            brd,
        )

        self._add_assumptions_and_constraints(
            pdf,
            content_width,
            brd,
        )

        self._add_risks_and_decisions(
            pdf,
            content_width,
            brd,
        )

        self._add_open_questions(
            pdf,
            content_width,
            brd,
        )

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        pdf.output(str(output))

        return str(output)

    def _add_title(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        pdf.add_page()

        # Document title
        pdf.set_x(self.LEFT_MARGIN)

        pdf.set_font(
            "Helvetica",
            "B",
            self.TITLE_FONT_SIZE,
        )

        pdf.multi_cell(
            w=width,
            h=10,
            text="BUSINESS REQUIREMENTS DOCUMENT",
        )

        pdf.ln(4)

        # Project title
        pdf.set_x(self.LEFT_MARGIN)

        pdf.set_font(
            "Helvetica",
            "B",
            self.PROJECT_TITLE_FONT_SIZE,
        )

        pdf.multi_cell(
            w=width,
            h=8,
            text=self._normalize_text(
                brd.project_overview.project_name
            ),
        )

        pdf.ln(5)

        # Horizontal separator
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)

        pdf.line(
            self.LEFT_MARGIN,
            pdf.get_y(),
            self.LEFT_MARGIN + width,
            pdf.get_y(),
        )

        pdf.ln(8)

    def _add_executive_summary(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "1. Executive Summary",
        )

        self._add_paragraph(
            pdf,
            width,
            brd.executive_summary.content,
        )

    def _add_project_overview(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "2. Project Overview",
        )

        self._add_labeled_value(
            pdf,
            width,
            "Project Name",
            brd.project_overview.project_name,
        )

        self._add_labeled_value(
            pdf,
            width,
            "Description",
            brd.project_overview.description,
        )

    def _add_business_objectives(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "3. Business Objectives",
        )

        self._add_bullets(
            pdf,
            width,
            brd.business_objectives.objectives,
        )

    def _add_scope(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "4. Scope",
        )

        self._add_subheading(
            pdf,
            width,
            "In Scope",
        )

        self._add_bullets(
            pdf,
            width,
            brd.scope.in_scope,
        )

        self._add_subheading(
            pdf,
            width,
            "Out of Scope",
        )

        self._add_bullets(
            pdf,
            width,
            brd.scope.out_of_scope,
        )

    def _add_stakeholders(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "5. Stakeholders",
        )

        for stakeholder in brd.stakeholders.stakeholders:
            details = self._normalize_text(
                stakeholder.name
            )

            if stakeholder.role:
                details += (
                    " -- "
                    f"{self._normalize_text(stakeholder.role)}"
                )

            if stakeholder.organization:
                details += (
                    f" ("
                    f"{self._normalize_text(stakeholder.organization)}"
                    f")"
                )

            self._add_bullet(
                pdf,
                width,
                details,
            )

    def _add_business_requirements(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "6. Business Requirements",
        )

        self._add_bullets(
            pdf,
            width,
            brd.business_requirements.requirements,
        )

    def _add_functional_requirements(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "7. Functional Requirements",
        )

        self._add_bullets(
            pdf,
            width,
            brd.functional_requirements.requirements,
        )

    def _add_non_functional_requirements(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "8. Non-Functional Requirements",
        )

        self._add_bullets(
            pdf,
            width,
            brd.non_functional_requirements.requirements,
        )

    def _add_assumptions_and_constraints(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "9. Assumptions & Constraints",
        )

        self._add_subheading(
            pdf,
            width,
            "Assumptions",
        )

        self._add_bullets(
            pdf,
            width,
            brd.assumptions_and_constraints.assumptions,
        )

        self._add_subheading(
            pdf,
            width,
            "Constraints",
        )

        self._add_bullets(
            pdf,
            width,
            brd.assumptions_and_constraints.constraints,
        )

    def _add_risks_and_decisions(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "10. Risks & Decisions",
        )

        self._add_subheading(
            pdf,
            width,
            "Risks",
        )

        self._add_bullets(
            pdf,
            width,
            brd.risks_and_decisions.risks,
        )

        self._add_subheading(
            pdf,
            width,
            "Decisions",
        )

        self._add_bullets(
            pdf,
            width,
            brd.risks_and_decisions.decisions,
        )

    def _add_open_questions(
        self,
        pdf: FPDF,
        width: float,
        brd: BRD,
    ) -> None:
        self._add_section_heading(
            pdf,
            width,
            "11. Open Questions",
        )

        self._add_bullets(
            pdf,
            width,
            brd.open_questions.questions,
        )

    @staticmethod
    def _add_section_heading(
        pdf: FPDF,
        width: float,
        text: str,
    ) -> None:
        pdf.ln(7)

        pdf.set_x(22)

        pdf.set_font(
            "Helvetica",
            "B",
            14,
        )

        pdf.multi_cell(
            w=width,
            h=8,
            text=BRDDocumentBuilder._normalize_text(
                text
            ),
        )

        # Subtle section separator
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)

        pdf.line(
            22,
            pdf.get_y(),
            22 + width,
            pdf.get_y(),
        )

        pdf.ln(4)

    @staticmethod
    def _add_subheading(
        pdf: FPDF,
        width: float,
        text: str,
    ) -> None:
        pdf.ln(3)

        pdf.set_x(22)

        pdf.set_font(
            "Helvetica",
            "B",
            11,
        )

        pdf.multi_cell(
            w=width,
            h=6,
            text=BRDDocumentBuilder._normalize_text(
                text
            ),
        )

        pdf.ln(2)

    @staticmethod
    def _add_paragraph(
        pdf: FPDF,
        width: float,
        text: str,
    ) -> None:
        pdf.set_x(22)

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        pdf.multi_cell(
            w=width,
            h=6.2,
            text=BRDDocumentBuilder._normalize_text(
                text
            ),
            align="J",
        )

        pdf.ln(2)

    @staticmethod
    def _add_labeled_value(
        pdf: FPDF,
        width: float,
        label: str,
        value: str,
    ) -> None:
        label = BRDDocumentBuilder._normalize_text(
            label
        )

        value = BRDDocumentBuilder._normalize_text(
            value
        )

        pdf.set_x(22)

        pdf.set_font(
            "Helvetica",
            "B",
            10,
        )

        label_width = pdf.get_string_width(
            f"{label}: "
        )

        pdf.write(
            6.2,
            f"{label}: ",
        )

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        # IMPORTANT:
        # The remaining width must account for
        # the label already written on this line.
        remaining_width = width - label_width

        pdf.multi_cell(
            w=remaining_width,
            h=6.2,
            text=value,
            align="J",
        )

        pdf.ln(2)

    @staticmethod
    def _add_bullet(
        pdf: FPDF,
        width: float,
        text: str,
    ) -> None:
        text = BRDDocumentBuilder._normalize_text(
            text
        )

        bullet_x = 25
        text_x = 31

        bullet_width = 4
        text_width = (
            width
            - (text_x - 22)
        )

        pdf.set_x(bullet_x)

        pdf.set_font(
            "Helvetica",
            "",
            10,
        )

        pdf.write(
            6.2,
            "-",
        )

        pdf.set_x(text_x)

        pdf.multi_cell(
            w=text_width,
            h=6.2,
            text=text,
            align="J",
        )

        pdf.ln(1)

    @staticmethod
    def _add_bullets(
        pdf: FPDF,
        width: float,
        items: list[str],
    ) -> None:
        if not items:
            pdf.set_x(22)

            pdf.set_font(
                "Helvetica",
                "I",
                10,
            )

            pdf.multi_cell(
                w=width,
                h=6.2,
                text="None specified.",
            )

            pdf.ln(1)

            return

        for item in items:
            BRDDocumentBuilder._add_bullet(
                pdf,
                width,
                item,
            )

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        """
        Converts common Unicode punctuation generated by the LLM
        into characters supported by the built-in Helvetica font.
        """

        replacements = {
            "—": "--",
            "–": "-",
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "…": "...",
            "•": "-",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text
