# Deferred Items — Phase 6

## 06-02: Pre-existing ruff findings (out of scope)

`ruff check app/app.py` reports 2 pre-existing issues unrelated to this
plan's changes (confirmed present in `app/app.py` at commit `784bb33`,
before plan 06-02 touched the file):

- Long-line import formatting for the `AppSetting, PriceRow` import (line 5).
- Unused `# noqa: E711` directive on the `_editable_cell` null-comparison
  (line 49) — `_editable_cell` is explicitly out of scope for this plan
  per the UI-SPEC "Do not touch `_editable_cell`" exception.

Not auto-fixed per the scope boundary rule (pre-existing issues in files
touched by the current task, but not introduced by it).
