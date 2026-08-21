# Research Environment — Installed Versions

Resolves 02-RESEARCH.md Open Question #2: does this environment actually match
STACK.md's pins? Recorded 2026-08-21 via `python -c "import sys; print(sys.version)"`
and `pip show pandas scikit-learn statsmodels pytest` from the project root.

| Package | Installed | STACK.md pin | Match? |
|---------|-----------|---------------|--------|
| Python | 3.12.5 | 3.11 or 3.12 | Yes |
| pandas | 2.2.3 | 3.0.5 | No |
| scikit-learn | 1.7.2 | 1.9.0 | No |
| statsmodels | 0.14.6 | 0.14.6 | Yes |
| pytest | 9.0.2 | 8.x | No (newer major, API-compatible for this phase's simple assertion-based tests) |

pandas 2.x installed: avoid pandas-3.0-only APIs in research scripts (e.g. do not
assume copy-on-write is the unconditional default — pandas 2.2.3 has it as opt-in via
`pd.options.mode.copy_on_write`, not the permanent pandas 3.0 default). Write code that
works correctly under pandas 2.2.3 semantics; do not rely on 3.0-only guarantees.
