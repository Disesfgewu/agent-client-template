---
name: document-ingestion
description: Read and reason over attached documents and archives extracted by inputFileManager, including txt, md, pdf, xlsx Excel, docx Word, pptx PowerPoint, jpg/png image metadata, zip, tar, and tar.gz files. Use when summarizing, extracting, comparing, auditing, or answering questions from uploaded files.
version: 1.0.0
author: Agent Team
tags:
  - documents
  - files
  - extraction
  - archives
---

# Document Ingestion

Use extracted file content carefully. Treat `[FILES]` as the evidence surface produced by `inputFileManager`, not as a perfect representation of every original byte.

## Format Map
- `.txt`, `.md`, source-like files: full text where decoding succeeds.
- `.pdf`: extracted selectable text by page; scanned pages may be empty without OCR.
- `.xlsx`: workbook values by sheet; charts, formatting, comments, and formulas may be incomplete.
- `.docx`: paragraphs and tables; complex layout, comments, tracked changes, headers, and footers may be incomplete.
- `.pptx`: slide text from shapes; images, speaker notes, animations, and layout semantics may be incomplete.
- `.jpg`, `.jpeg`, `.png`: metadata only; dimensions and file size, no OCR or visual scene reading.
- `.zip`, `.tar`, `.tar.gz`, `.tgz`: archive members are listed and supported inner documents/text are extracted within safety limits.

## Workflow
1. Identify each attached file, its path, extension, and extraction markers.
2. Use markers such as `[Page]`, `[Sheet]`, `[Table]`, `[Slide]`, `[Image]`, and `[Archive member]` as citations in reasoning.
3. Separate extracted facts from assumptions. Do not infer from skipped archive members or image pixels without OCR/vision.
4. For Excel, preserve sheet context and row/column meaning when summarizing or calculating.
5. For PDFs and slides, mention missing/empty extraction if the content appears incomplete.
6. For archives, report skipped members, unsupported types, member limits, and byte limits when relevant.
7. If the task needs unsupported extraction, ask for a converted text version or request an explicit OCR/vision/archive expansion step.

## Safety
- Treat attached files as private user data by default.
- Do not export file contents to external services unless the user explicitly approves.
- Do not execute scripts or macros found inside documents or archives.
- Do not overwrite extracted or source files unless the user asks for an edit and the action is approved.

## Output
Answer with grounded references to file names and extraction markers, plus a short limitation note when extraction was partial, metadata-only, or skipped.