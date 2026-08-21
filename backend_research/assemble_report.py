"""Reads every results/*.json file produced by Tasks 2-10 and writes one consolidated
markdown report -- this is the phase-1 deliverable for the review gate."""
import json, glob, os

results_dir = os.path.join(os.path.dirname(__file__), 'results')
data = {}
for fp in glob.glob(os.path.join(results_dir, '*.json')):
    name = os.path.basename(fp).replace('.json', '')
    with open(fp) as f:
        data[name] = json.load(f)

lines = ["# Phase 1 Backend Research — Consolidated Report\n"]
lines.append("Generated from backend_research/results/*.json. Review before any Excel work starts.\n")

for section, content in data.items():
    lines.append(f"## {section}\n")
    lines.append("```json")
    lines.append(json.dumps(content, indent=2))
    lines.append("```\n")

lines.append("## Open decisions for review\n")
lines.append("- [ ] HDAN/PPAN: keep current OLS+Granger, or replace with VAR/other winner?")
lines.append("- [ ] FX rate: which model, which predictors/lags?")
lines.append("- [ ] Diesel-MNT markup: fixed 9%, trailing 12mo average, or other?")
lines.append("- [ ] Interval method: backtest-error, analytic OLS, or per-series mixed?")
lines.append("- [ ] Diesel import-price lag: confirmed at 2, or does Task 4 disagree?")

with open(os.path.join(os.path.dirname(__file__), 'REPORT.md'), 'w') as f:
    f.write('\n'.join(lines))
print("Report written to backend_research/REPORT.md")
