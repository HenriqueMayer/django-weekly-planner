# Phase G — Card Attachments

**Status:** complete

## Delivered

- Added validated `CardAttachment` uploads for cards.
- Added a 10 MB size limit and allow-listed file extensions.
- Added attachment links and deletion controls in the detail panel.
- Added ownership-scoped upload and deletion endpoints.
- Added `attachment_added` and `attachment_deleted` activity events.
- Added local media serving for development and admin registration.

## Rules

- Supported extensions: CSV, DOC, DOCX, JPG, JPEG, MD, PDF, PNG, and TXT.
- The authenticated user is always recorded as uploader.
- Files are deleted from storage before their database row is removed.
- Card deletion cascades to attachment metadata; storage cleanup is handled by
  the explicit deletion path.

## Verification

- Attachment validation, upload, deletion, and ownership tests.
- Full test suite count is tracked in `docs/ARCHITECTURE.md`.
