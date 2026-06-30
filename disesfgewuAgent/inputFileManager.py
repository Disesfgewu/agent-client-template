import asyncio
import os
from pathlib import Path
from typing import Callable
from pypdf import PdfReader
from pptx import Presentation
from openpyxl import load_workbook
from docx import Document


class inputFileManager:

    SUPPORTED_FORMATS = {".txt", ".md", ".pdf", ".xlsx", ".docx", ".pptx"}

    @staticmethod
    def extract(filepath: str) -> str:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = path.suffix.lower()
        if ext in (".txt", ".md"):
            return inputFileManager._extractTxt(filepath)
        elif ext == ".pdf":
            return inputFileManager._extractPdf(filepath)
        elif ext == ".xlsx":
            return inputFileManager._extractXlsx(filepath)
        elif ext == ".docx":
            return inputFileManager._extractDocx(filepath)
        elif ext == ".pptx":
            return inputFileManager._extractPptx(filepath)
        else:
            raise ValueError(
                f"Unsupported format: {ext}. "
                f"Supported: {', '.join(sorted(inputFileManager.SUPPORTED_FORMATS))}"
            )

    @staticmethod
    def _extractTxt(filepath: str) -> str:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # latin-1 maps every byte, so this never raises and preserves
            # the original bytes rather than crashing on non-UTF-8 input.
            with open(filepath, "r", encoding="latin-1") as f:
                return f.read()

    @staticmethod
    def _extractPdf(filepath: str) -> str:

        reader = PdfReader(filepath)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {i + 1}]\n{text}")
        return "\n\n".join(pages) if pages else ""

    @staticmethod
    def _extractXlsx(filepath: str) -> str:

        wb = load_workbook(filepath, read_only=True, data_only=True)
        sheets = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(cell) if cell is not None else "" for cell in row]
                if any(cells):
                    rows.append(", ".join(cells))
            if rows:
                sheets.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))

        wb.close()
        return "\n\n".join(sheets) if sheets else ""

    @staticmethod
    def _extractDocx(filepath: str) -> str:

        doc = Document(filepath)
        parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)

        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    table_rows.append(" | ".join(cells))
            if table_rows:
                parts.append("[Table]\n" + "\n".join(table_rows))

        return "\n\n".join(parts) if parts else ""

    @staticmethod
    def _extractPptx(filepath: str) -> str:
        prs = Presentation(filepath)
        slides = []

        for i, slide in enumerate(prs.slides):
            slide_parts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_parts.append(shape.text.strip())
            if slide_parts:
                slides.append(f"[Slide {i + 1}]\n" + "\n".join(slide_parts))

        return "\n\n".join(slides) if slides else ""

    @staticmethod
    async def decompose(filepaths: list, countTokens: Callable[[str], int]) -> tuple:
        parts = []
        for filepath in filepaths:
            text = await asyncio.to_thread(inputFileManager.extract, filepath)
            filename = os.path.basename(filepath)
            parts.append(f"[{filename}]\n{text}")

        result = "[FILES]\n" + "\n\n".join(parts)
        token_count = countTokens(result)
        return result, token_count

    @staticmethod
    def decomposeSync(filepaths: list, countTokens: Callable[[str], int]) -> tuple:
        parts = []
        for filepath in filepaths:
            text = inputFileManager.extract(filepath)
            filename = os.path.basename(filepath)
            parts.append(f"[{filename}]\n{text}")

        result = "[FILES]\n" + "\n\n".join(parts)
        token_count = countTokens(result)
        return result, token_count
