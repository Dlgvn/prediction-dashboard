---
slug: readme-weekly-note
created: 2026-08-23
---

# Update README.md for weekly-cadence research

## Task

1. Add `AN price weekly.csv` to the "What's in this folder" table — weekly-driver source
   (JKM/Henry Hub/UK/Netherlands gas, US/China corn, Middle East Ammonia, Black Sea/China Urea),
   used by `backend_research/run_weekly_candidates.py`.
2. Add a short note near "Open flag: the markup rate" documenting that weekly-cadence
   forecasting was backtested and is a no-go for now — monthly VAR(HDAN,PPAN) remains the model
   in use. Reference `backend_research/REPORT.md`'s "Weekly cadence (Phase 1 follow-up)" section
   and `.planning/STATE.md`'s updated blocker note.

No changes to workbook structure/model description sections.
