from pathlib import Path

from fpdf import FPDF

from models.standard_document import StandardDocument


class ProjectDocumentBuilder:
    """
    Builds a compact PDF containing multiple StandardDocuments.

    The generated PDF is intended as an input artifact for
    downstream document intelligence processing.
    """

    LEFT_MARGIN = 12
    RIGHT_MARGIN = 12
    TOP_MARGIN = 12
    BOTTOM_MARGIN = 12

    def build(
        self,
        documents: list[StandardDocument],
        output_path: str,
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

        for index, document in enumerate(documents, start=1):

            # Start the first document on the first page.
            # Subsequent documents continue naturally.
            if index == 1:
                pdf.add_page()
            else:
                pdf.ln(4)

            # Document heading
            pdf.set_x(self.LEFT_MARGIN)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(
                w=content_width,
                h=7,
                text=f"DOCUMENT {index}",
            )

            # Metadata
            metadata = self._build_metadata(document)

            if metadata:
                pdf.ln(1)

                for line in metadata:
                    pdf.set_x(self.LEFT_MARGIN)
                    pdf.set_font("Helvetica", "", 8)
                    pdf.multi_cell(
                        w=content_width,
                        h=4.5,
                        text=line,
                    )

            # Content heading
            pdf.ln(2)

            pdf.set_x(self.LEFT_MARGIN)
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(
                w=content_width,
                h=5,
                text="CONTENT",
            )

            # Document content
            pdf.ln(1)

            pdf.set_x(self.LEFT_MARGIN)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(
                w=content_width,
                h=4.5,
                text=document.content,
            )

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        pdf.output(str(output))

        return str(output)

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

        if document.created_at:
            metadata.append(
                f"Created At: {document.created_at}"
            )

        if document.participants:
            metadata.append(
                f"Participants: {', '.join(document.participants)}"
            )

        return metadata
