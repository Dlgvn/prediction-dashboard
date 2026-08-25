# Phase 12: Fan Chart Legend/Axis Fix — Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the fan chart's legend overlapping its axis labels/annotation. Root cause confirmed by reading `state.py`: `forecast_chart_figure`'s `legend=dict(orientation="h")` has no explicit `y`/`yanchor` position, so Plotly defaults it near the top of the plot area (y≈1), colliding with the tight `t=16` top margin and the "Forecast start" `add_vline` annotation, which is also anchored `"top left"`.

In scope: `forecast_chart_figure`'s legend positioning and margin adjustment; per D-02 below, `historical_chart_figure`'s layout for consistency (though it currently has `showlegend=False` and has no actual collision, since it's single-series).
Out of scope: any change to chart data, trace construction, colors (Phase 11 territory), or the "Forecast start" vline's existence/wording.
</domain>

<decisions>
## Implementation Decisions

### Legend position
- **D-01:** Move the legend to a horizontal orientation below the plot area (not top-left/top-right outside the plot). Requires an explicit `y` below 0 (e.g. `y=-0.2` to `-0.3`, tuned during implementation) with `yanchor="top"`, `x=0.5`, `xanchor="center"` for horizontal centering, plus an increased bottom margin (`b=`) so the legend has room and doesn't get clipped or overlap the x-axis tick labels/title.

### Chart scope
- **D-02:** Apply the same layout treatment (margin/legend positioning approach) to both `historical_chart_figure` and `forecast_chart_figure` for visual consistency, even though `historical_chart_figure` currently has `showlegend=False` (single series, no legend rendered) and has no actual overlap bug today.

### Claude's Discretion
- Exact `y`/margin pixel values — tune so the legend clears the x-axis title without excessive whitespace; verify visually across the existing viewport breakpoints already established in Phase 6/7 (desktop, tablet, mobile).
- Whether the "Forecast start" vline annotation needs `annotation_position` or `annotation_y` adjustment now that the legend is out of the top area — verify no new collision is introduced between the vline annotation and the plot title/axis area.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing code (primary implementation surface)
- `app/app/state.py` — `historical_chart_figure` (~line 265, `update_layout` blocks at ~283 and ~306) and `forecast_chart_figure` (~line 651, the `legend=dict(orientation="h")` at ~767 with no y position, `add_vline` "Forecast start" annotation at ~757, and the full `update_layout` block at ~763-772)
- `app/app/theme.py` — mode-aware color tokens (`t["MUTED_TEXT"]`, `t["BORDER"]`, `t["ACCENT"]`) already used by these figure builders per Phase 11 — do not reintroduce hardcoded colors

### v1.3 milestone research (MANDATORY)
- `.planning/research/SUMMARY.md` — Phase 2 (this phase) is flagged "standard patterns, skip deep research" — well-documented Plotly `update_layout()` API, isolated single-file change
- `.planning/research/PITFALLS.md` — Pitfall 5: fan chart legend fix must not collide with the "Forecast start" vline annotation; must apply consistently to both `historical_chart_figure` and `forecast_chart_figure`; must leave `aria_label` props in `app.py` untouched (this phase does not touch `app.py` at all)

### Prior phase precedent
- `.planning/phases/11-background-fix-theme-toggle/` — established the `tokens(self.theme_mode)` pattern (`t = tokens(self.theme_mode)`) both figure builders already use; this phase must not disturb that

### Project-level
- `.planning/REQUIREMENTS.md` — VIS-04
- `.planning/ROADMAP.md` — Phase 12 entry

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Both figure builders already share near-identical `update_layout()` structure (margin, plot_bgcolor, paper_bgcolor, font) — the legend/margin fix should be applied as parallel edits to both, not a new shared helper (matches the existing code's duplication level, not introducing new abstraction).

### Established Patterns
- Color values always resolve through `t = tokens(self.theme_mode)` (Phase 11) — no hardcoded hex in this phase's changes either.
- `margin=dict(l=40, r=16, t=16, b=40)` is the current shared margin dict literal in both figures — increasing `b` for the new below-plot legend is a straightforward value change, not a restructure.

### Integration Points
- No `app.py` changes needed — this is entirely a `state.py` Plotly layout change.
- The `aria_label` props on the chart-wrapping `rx.box` in `app.py` (`historical_chart()`, `forecast_chart()`) are untouched — verify they still make sense (they describe the chart's purpose, not its exact layout).

</code_context>

<specifics>
## Specific Ideas

No new visual references — this is a targeted Plotly layout tuning fix within the existing Phase 6 chart aesthetic.

</specifics>

<deferred>
## Deferred Ideas

None — phase scope is narrow and fully covered by the decisions above.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-fan-chart-legend-axis-fix*
*Context gathered: 2026-08-24*
