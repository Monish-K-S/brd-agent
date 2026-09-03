from pathlib import Path

from fpdf import FPDF

from app.ai.models.standard_document import StandardDocument


class ProjectDocumentBuilder:
    """
    Builds a compact PDF containing multiple StandardDocuments.

    The generated PDF is used as input for
    Sarvam Document AI extraction.
    """

    LEFT_MARGIN = 10
    RIGHT_MARGIN = 10
    TOP_MARGIN = 10
    BOTTOM_MARGIN = 10

    FONT_SIZE = 8
    LINE_HEIGHT = 4

    def build(
        self,
        documents: list[StandardDocument],
        output_path: str | Path,
    ) -> str:
        pdf = FPDF()

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

        pdf.add_page()

        for index, document in enumerate(
            documents,
            start=1,
        ):
            if index > 1:
                pdf.ln(4)

            self._add_document(
                pdf=pdf,
                document=document,
                index=index,
                content_width=content_width,
            )

        output = Path(output_path)
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        pdf.output(str(output))

        return str(output)

    def _add_document(
        self,
        pdf: FPDF,
        document: StandardDocument,
        index: int,
        content_width: float,
    ) -> None:
        # Document heading
        pdf.set_x(self.LEFT_MARGIN)
        pdf.set_font(
            "Helvetica",
            "B",
            10,
        )
        pdf.multi_cell(
            w=content_width,
            h=5,
            text=f"DOCUMENT {index}",
        )

        # Metadata
        metadata = self._build_metadata(document)

        if metadata:
            pdf.ln(1)

            pdf.set_font(
                "Helvetica",
                "",
                7,
            )

            for line in metadata:
                pdf.set_x(self.LEFT_MARGIN)

                pdf.multi_cell(
                    w=content_width,
                    h=3.5,
                    text=line,
                )

        # Content
        pdf.ln(1)

        pdf.set_x(self.LEFT_MARGIN)
        pdf.set_font(
            "Helvetica",
            "B",
            8,
        )

        pdf.multi_cell(
            w=content_width,
            h=4,
            text="CONTENT",
        )

        pdf.ln(1)

        pdf.set_x(self.LEFT_MARGIN)
        pdf.set_font(
            "Helvetica",
            "",
            self.FONT_SIZE,
        )

        pdf.multi_cell(
            w=content_width,
            h=self.LINE_HEIGHT,
            text=document.content,
        )

    @staticmethod
    def _build_metadata(
        document: StandardDocument,
    ) -> list[str]:
        metadata: list[str] = []

        if document.source_type:
            metadata.append(
                f"Source Type: {document.source_type}"
            )

        if document.title:
            metadata.append(
                f"Title: {document.title}"
            )

        if document.author:
            metadata.append(
                f"Author: {document.author}"
            )

        if document.source_created_at:
            metadata.append(
                f"Created At: {document.source_created_at}"
            )

        if document.participants:
            metadata.append(
                "Participants: "
                f"{', '.join(document.participants)}"
            )

        return metadata
