---
name: file-io
description: Work safely with files, directories, encodings, structured documents, images, archives, and data interchange formats. Use when reading, writing, transforming, validating, extracting, or organizing local files including txt, md, pdf, xlsx, docx, pptx, jpg, png, zip, tar, and tar.gz.
version: 1.1.0
author: Agent Team
tags:
  - files
  - io
  - data
  - automation
---

# File IO

Handle files predictably, preserve user data, and choose parsers over brittle string processing.

## InputFileManager Coverage
Attached files are preprocessed by `inputFileManager` before they appear in `[FILES]`:

- Text-like: `.txt`, `.md`, source files, `.json`, `.csv`, `.yaml`, `.xml`, etc. are read as text with UTF-8 then latin-1 fallback.
- PDF: `.pdf` text is extracted per page as `[Page N]`.
- Excel: `.xlsx` values are extracted per sheet as `[Sheet: name]`; formulas are read as cached values when available.
- Word: `.docx` paragraphs and tables are extracted; tables are marked as `[Table]`.
- PowerPoint: `.pptx` text shapes are extracted per slide as `[Slide N]`.
- Images: `.jpg`, `.jpeg`, `.png` return metadata and dimensions only; no OCR or visual understanding is performed by `inputFileManager`.
- Archives: `.zip`, `.tar`, `.tar.gz`, `.tgz` are safely listed and supported inner members are extracted within member-count and byte limits.

## When to Use
- Reading or writing text, JSON, YAML, CSV, Excel, XML, Markdown, PDF, DOCX, PPTX, images, archives, or source files.
- Renaming, organizing, validating, converting, or extracting local file content.
- Explaining what can and cannot be inferred from `[FILES]` extracted content.

## Safety Rules
1. Inspect paths before edits. Avoid destructive operations unless explicitly requested.
2. Preserve encodings, line endings, metadata, and formatting where practical.
3. Use structured parsers for structured formats: JSON/YAML/CSV/Excel/XML/HTML.
4. For archives, list members and enforce limits before extracting; never trust archive paths for writes.
5. For images, do not claim text or visual facts unless OCR/vision was explicitly performed by another tool.
6. Write atomically when possible: temporary file, validation, then replace.
7. Treat user files as authoritative; never overwrite unrelated changes.

## Workflow
- List candidate files, sample representative content, and infer format from content as well as extension.
- Validate inputs before transformation and outputs after transformation.
- For large files, stream or chunk rather than loading everything into memory.
- For binary or proprietary formats, use maintained libraries and verify extracted content.
- If `[FILES]` says a member was skipped, too large, unsupported, or metadata-only, report that limitation instead of guessing.

## Output
State files read, files changed, validation performed, skipped files, extraction limitations, and any assumptions about encoding or format.