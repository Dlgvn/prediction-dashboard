# Phase 22: Weekly Granularity Toggle & UI - Research

**Researched:** 2026-09-01
**Domain:** Reflex (Python) state/UI wiring — mixed-cadence (monthly/weekly) toggle over an existing shipped dashboard
**Confidence:** HIGH for everything scoped to the existing (already-read, already-shipped) `app.py`/`state.py`/`theme.py`/`forecasting.py` code. MEDIUM-LOW for anything that depends on Phase 21's exact function/constant names, which do not exist in the codebase yet (verified: `app/app/forecasting.py` read in full this session, contains zero `weekly`-prefixed symbols as of 2026-09-01).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Toggle placement**: Next to the existing horizon selector, in the Forecast tab —
  `horizon_control()` in `app/app/app.py` (lines ~277-308) is the existing component to
  extend/sit beside. The horizon control and granularity toggle are closely related
  (horizon *range* changes depending on granularity — 1-12 months vs. up to 5 weeks per
  Phase 21's `MAX_HORIZON_WEEKLY`), so they belong together, not scattered across tabs.
- **Diesel-USD/Diesel-MNT weekly-mode treatment**: Grayed-out/dimmed card stays in its
  normal grid position, showing the last-known monthly forecast values visually muted, with
  a small badge/label explaining "Monthly data only" (or similar wording). NOT a blank
  placeholder with no numbers, and NOT hidden entirely — the card's presence and its
  (dimmed) monthly numbers make clear this series simply doesn't have weekly granularity,
  rather than looking broken or making the user wonder where it went.
- Single **global** Monthly/Weekly toggle — one state var drives both the Forecast tab
  chart AND the Summary tab cards together. No per-series toggles (explicitly an
  anti-feature — "two reading speeds on one screen").
- Toggle **persists** across reload/visit — reuse the exact mechanism `DashboardState`
  already uses for `theme_mode` persistence (its own localStorage-style key, per Phase 11's
  precedent — check `state.py` for the exact pattern: likely `rx.Cookie` or a
  `LocalStorage`-backed Var, or an `AppSetting` DB row like `markup_pct`).
- Default stays **Monthly** — Weekly is opt-in, never auto-selected even though some weekly
  models are more accurate than their monthly counterparts (explicit anti-feature per
  FEATURES.md: "Auto-defaulting to Weekly mode 'because it's more accurate' removes user
  agency").
- Weekly horizon is denominated in **weeks**, capped to whatever Phase 21's
  `MAX_HORIZON_WEEKLY` constant turns out to be (research flagged this as validated up to
  5 weeks, per the backtest's `horizon=5` — confirm the actual constant name/value from
  Phase 21's finished code before wiring the slider's max).
- Each weekly-capable series' (HDAN/PPAN/FX) summary card must show the **correct weekly
  model name + MAPE** when in Weekly mode — read from Phase 21's `WEEKLY_MODEL_INFO`, not
  a stale monthly `MODEL_INFO` figure. This is the same card component already showing
  `MODEL_INFO`-derived text for monthly (see `summary_cards()`/wherever the existing
  provenance line renders) — branch its data source on the granularity state var, don't
  build a parallel card component.
- Weekly forecast chart/table dates must be **real week-ending dates**, not monthly ticks
  relabeled — the x-axis/date column should come from the actual `WeeklyPriceRow`/weekly
  forecast index, which already carries real dates.
- Should-have (cheap, recommended if time allows): fold the weekly-vs-monthly MAPE delta
  into the provenance line itself (e.g. "7.25% MAPE weekly · 9.49% monthly") rather than a
  separate comparison widget.

### Non-goals (explicit)

- No weekly Data Entry UI.
- No per-series granularity override.
- No horizon extension beyond what Phase 21 actually validated.
- No changes to the existing monthly Forecast/Summary rendering when Monthly is selected —
  Monthly mode's current behavior must be pixel-identical to today post-implementation
  (regression risk to watch).

### Claude's Discretion

- Exact Reflex component choice for the toggle itself (`rx.segmented_control`, `rx.switch`,
  `rx.tabs`, or a styled `rx.hstack` of two buttons) — match the existing design system's
  established look.
- Exact wording of the Diesel "Monthly data only" badge — keep it short, non-alarming.
- Whether granularity state lives as a new `DashboardState` var or is grouped with the
  existing `horizon_months`/theme-mode vars — executor's call on organization, but must
  follow whatever persistence pattern `theme_mode` already established.
- Exact grid/layout mechanics for keeping Diesel's card in its normal position while dimmed
  — CSS opacity/color-token approach, informed by `theme.py`'s existing muted/disabled
  token vocabulary if one exists.

### Deferred Ideas (OUT OF SCOPE)

None raised beyond what's already tracked in REQUIREMENTS.md's v2.1+ Deferred section
(weekly Data Entry UI, per-series granularity mixing, horizon extension beyond backtest,
auto-defaulting to Weekly).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| WKUI-03 | Global Monthly/Weekly toggle drives both Forecast chart and Summary cards | Architecture Pattern 1 (`DashboardState.granularity`), Pattern 5 (toggle component) — single state var read by both `summary_cards`/`forecast_chart_figure`/`forecast_table_rows` |
| WKUI-04 | Selected granularity persists across reload/visit | Pattern 1 — `rx.LocalStorage`, mirroring `theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")` exactly (`app/app/state.py:216`) |
| WKUI-05 | Diesel-USD/Diesel-MNT show explicit always-visible "monthly only" muted state | Pattern 3 (card dimming), Pitfall 6 (Diesel-USD has no summary card today — requirement/app mismatch flagged) |
| WKUI-06 | Weekly horizon denominated in weeks, capped to validated range | Pattern 2 (`horizon_weeks` separate var, `horizon_max` computed var, slider wiring) — contingent on Phase 21's `MAX_HORIZON_WEEKLY` |
| WKUI-07 | Weekly-capable series' cards show correct weekly model name + MAPE | Pattern 4 (provenance branching via `WEEKLY_MODEL_INFO`) — contingent on Phase 21's `WEEKLY_MODEL_INFO` |
| WKUI-08 | Weekly chart/table dates are real week-ending dates | Pattern 6 (chart date math), Pattern 7 (table date math) — contingent on Phase 21's `forecast_all_weekly`/`_to_rows` step-index shape |
</phase_requirements>

## Summary

This phase is pure UI/state wiring on top of an already-shipped, well-established Reflex
app. Every mechanism the toggle needs already has a working precedent in this exact
codebase: `theme_mode`'s `rx.LocalStorage` persistence (Phase 11), `active_section`'s
single global state var driving multiple tab views (Phase 14), and `summary_cards`'/
`forecast_chart_figure`'s existing "read one computed dict, branch on a key" pattern
(Phase 3/5/6/8/13). Nothing here requires a new library or a new architectural pattern —
it requires careful, additive branching so Monthly mode stays pixel-identical (the
phase's own explicit regression constraint) while Weekly mode reuses the same components
with a different data source.

The one real risk is **not** technical difficulty — it's scope precision on two points
CONTEXT.md left as discretion: (1) the Summary tab's card grid today has exactly **one**
Diesel card (`diesel_mnt`; `diesel_usd_ton` is deliberately excluded from
`SUMMARY_CARD_SERIES` per `state.py:118-122`'s own docstring), so WKUI-05's "Diesel-USD
and Diesel-MNT cards" language doesn't map 1:1 onto today's app — Diesel-USD's honest
"monthly only" surface has to be the Forecast tab's series selector/table instead, not a
second summary card; and (2) the horizon slider must NOT reuse `horizon_months` directly
for weekly (that would either break Monthly's pixel-identical guarantee when switching
back, or force awkward clamping) — a **separate** `horizon_weeks` state var, chosen via a
computed `active_horizon`/`horizon_max` pair, is the safe design.

This phase is also **hard-blocked** on Phase 21 landing: `app/app/forecasting.py`
currently has zero weekly symbols (`forecast_all_weekly`, `WEEKLY_MODEL_INFO`,
`MAX_HORIZON_WEEKLY`, `forecast_weekly_hdan/ppan/fx` all do not exist yet — verified by
reading the full file this session). Everything below that touches those names is marked
**[CONTINGENT ON PHASE 21]** and must be re-verified against Phase 21's actual shipped
code (not this document, not 21-RESEARCH.md's proposed names) before the plan is
finalized.

**Primary recommendation:** Add a `granularity: str = rx.LocalStorage("monthly", name="pd_granularity")` var and a parallel `horizon_weeks: int = 4` var to `DashboardState`; branch `summary_cards`, `forecast_chart_figure`, and `forecast_table_rows` on `self.granularity` inline (same function, same component, new `if`/`rx.cond` branch) rather than building parallel weekly-only components; render the toggle as `rx.segmented_control.root(...)` beside `horizon_control()`'s slider; dim Diesel's card via an opacity wrapper (not a new theme palette) driven by a new `is_dimmed`/`cadence_badge` key pair added to every `summary_cards` dict entry.

## Standard Stack

### Core

No new packages. This phase uses only what's already installed in `app/.venv`.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| Reflex | 0.9.8.post1 (per CLAUDE.md, unchanged) | `rx.segmented_control`, `rx.LocalStorage`, `rx.cond` — all already used elsewhere in this app | Existing project stack; `rx.segmented_control.root`/`.item` confirmed current in Reflex's official docs [CITED: https://reflex.dev/docs/library/disclosure/segmented-control/] |

### Alternatives Considered (toggle component)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rx.segmented_control` | `rx.tabs` (as `nav_bar()` already does) | Tabs read as page-level navigation (matches `nav_bar()`'s existing "Summary/Forecast/Data Entry" semantics) — reusing tabs for a data-mode toggle risks visually implying it's a 4th nav section, not a settings control. Segmented control is the more correct Radix primitive for "pick one of two mutually-exclusive display modes," and Reflex ships it as a first-class wrapped component. |
| `rx.segmented_control` | `rx.switch` (as `theme_toggle()`/`history_toggle()` already use) | A boolean switch works but loses the explicit "Monthly" / "Weekly" labels a two-way switch usually needs an adjacent caption for — segmented control shows both labels inline with no extra text needed, and better matches the horizon control's already-labeled, always-visible style. Either is defensible; segmented control is recommended for label clarity, not because switch is wrong. |
| `rx.segmented_control` | hand-rolled `rx.hstack` of two `rx.button`s with conditional `color_scheme` | Reflex's own component already implements the exact interaction (single-select, `on_change`, ARIA roles via Radix) — hand-rolling reintroduces the class of problem `nav_bar()`'s docstring specifically avoided by using `rx.tabs` instead of hand-rolled buttons ("tablist/tab/aria-selected/keyboard-navigation wiring comes for free from Radix rather than being hand-rolled," `app.py:823-826`). Don't hand-roll what Radix/Reflex already ships. |

**Installation:** None required — no new pip/npm packages.

**Version verification:** Not applicable (zero new dependencies). Confirmed via WebFetch against Reflex's own docs [CITED: reflex.dev/docs/library/disclosure/segmented-control/, fetched 2026-09-01] that `rx.segmented_control.root` accepts `value`/`default_value`/`on_change`/`size`/`variant`/`color_scheme`/`radius`, and `rx.segmented_control.item(label, value=...)` — this matches the calling convention already used for `rx.tabs.trigger` elsewhere in `app.py`, so no new mental model for the executor.

## Architecture Patterns

### Recommended file/module changes

No new files. All changes land in the three files already read in full this session:

```
app/app/state.py       # new DashboardState vars + computed vars + branching in
                        # summary_cards / forecast_chart_figure / forecast_table_rows
app/app/app.py          # horizon_control() extended with the toggle; _summary_card()
                        # extended with dim/badge rendering; forecast_table() branches
                        # on granularity for its column set
app/app/theme.py        # one new constant (dim opacity value) — optional, see Pattern 3
app/app/forecasting.py  # NOT touched by this phase — Phase 21 owns all edits here
```

---

### Pattern 1: Granularity state var + persistence (WKUI-03, WKUI-04)

**What:** Mirror `theme_mode`'s exact `rx.LocalStorage` mechanism, with the phase's own
key, defaulting to `"monthly"` per the locked non-goal ("Weekly is opt-in, never
auto-selected").

**Verified existing precedent** (`app/app/state.py:216`):
```python
theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")
```

**Recommended addition**, placed near `theme_mode`/`active_section` in `DashboardState`:
```python
# WKUI-03/WKUI-04: global granularity toggle. Mirrors theme_mode's exact
# rx.LocalStorage mechanism (own key, own default) so it persists across
# reload/visit independently of theme_mode. Deliberately a plain "monthly"/
# "weekly" string, not a bool, matching active_section's string-enum style
# (state.py:222) rather than theme_mode's implicit-boolean two-value style,
# since a third value is conceivable later (though not planned) and string
# equality checks read more clearly in rx.cond(... == "weekly", ...) call
# sites than a bareword bool would.
granularity: str = rx.LocalStorage("monthly", name="pd_granularity")

def set_granularity(self, value: str) -> None:
    """Assign the toggle's value; ignores unrecognized values defensively
    (mirrors select_series'/select_forecast_series' "ignore unknown label"
    guard, state.py:508-512/524-528). Also falls the Forecast tab's
    series selector back to a weekly-capable series if the user is
    currently viewing a Diesel series when switching to Weekly, so the
    chart never tries to render a series with no weekly data (see
    Pattern 6).
    """
    if value not in ("monthly", "weekly"):
        return
    self.granularity = value
    if value == "weekly" and self.forecast_series not in WEEKLY_CAPABLE_SERIES:
        self.forecast_series = "hdan"
```

Unlike `theme_mode`'s toggle (which fires a two-item `on_click` chain —
`[DashboardState.toggle_theme_mode, rx.toggle_color_mode]` — because it must also flip
Radix's own color-mode chrome, `app.py:812-817`), granularity has no equivalent second
system to synchronize, so a single `on_change=DashboardState.set_granularity` is
sufficient (segmented control's `on_change` already passes the selected value as the
handler's argument, matching `set_active_section`'s calling convention).

---

### Pattern 2: Horizon control — separate weekly var, not shared clamping (WKUI-06)

**What:** Add `horizon_weeks` as an independent var from `horizon_months`, plus two
computed vars (`active_horizon`, `horizon_max`) the slider reads from, so Monthly mode's
`horizon_months`/`MAX_HORIZON`/slider behavior is untouched byte-for-byte (satisfies the
locked "Monthly mode pixel-identical" constraint) while Weekly mode gets its own
independently-clamped range.

**Why not reuse `horizon_months` for both:** `set_horizon`'s existing clamp
(`app/app/state.py:514-522`) is `max(1, min(MAX_HORIZON, int(value[0])))` — hard-coded to
`MAX_HORIZON = 12`. If the same var were shared across modes, switching Weekly -> Monthly
after having dragged the weekly slider to e.g. week 5 would either silently reinterpret
"5" as 5 months (wrong value carried over) or require an explicit re-clamp/reset on every
toggle flip (extra state-transition surface, more to regress-test). A dedicated var
avoids both: each mode's slider position is independently remembered, matching how
`show_all_history` and `active_section` are already independent, un-entangled toggles in
this file.

```python
# WKUI-06: independent from horizon_months (see rationale above) — NOT
# persisted (matches horizon_months' existing non-persisted precedent;
# Phase 5 never persisted horizon_months either, and CONTEXT.md's locked
# decisions only require the granularity CHOICE to persist, not the
# horizon value within each mode).
horizon_weeks: int = 4  # [CONTINGENT ON PHASE 21]: pick a default <= MAX_HORIZON_WEEKLY;
                         # 4 matches the backtest's PRIMARY validated horizon (mape_h4)
                         # per 21-CONTEXT.md/21-RESEARCH.md -- confirm against Phase 21's
                         # actual constant before locking this literal.

@rx.var
def active_horizon(self) -> int:
    """Slider value source — branches so the existing horizon_months slider
    keeps working exactly as today when granularity == 'monthly'."""
    return self.horizon_weeks if self.granularity == "weekly" else self.horizon_months

@rx.var
def horizon_max(self) -> int:
    """[CONTINGENT ON PHASE 21]: MAX_HORIZON_WEEKLY must be imported from
    forecasting.py once Phase 21 lands, exactly as MAX_HORIZON already is
    (state.py:20-24's existing import block)."""
    return MAX_HORIZON_WEEKLY if self.granularity == "weekly" else MAX_HORIZON

@rx.var
def horizon_caption(self) -> str:
    """Replaces horizon_control()'s inline rx.cond text-concatenation
    (app.py:300-303) with one computed var covering both units. Either
    approach (computed var vs. inline rx.cond) is fine; a computed var is
    slightly easier to unit-test in isolation."""
    if self.granularity == "weekly":
        n = self.horizon_weeks
        return f"{n} week" if n == 1 else f"{n} weeks"
    n = self.horizon_months
    return f"{n} month" if n == 1 else f"{n} months"

def set_horizon(self, value: list[int]) -> None:
    """Single on_change call site (matches the existing "one slider, one
    handler" shape) — branches internally on granularity to write to the
    correct backing var with the correct clamp bound, per Pattern 2's
    rationale above."""
    if not value:
        return
    if self.granularity == "weekly":
        self.horizon_weeks = max(1, min(MAX_HORIZON_WEEKLY, int(value[0])))
    else:
        self.horizon_months = max(1, min(MAX_HORIZON, int(value[0])))
```

**`horizon_control()` in `app.py`** (extends the existing function; existing slider
`min=1`/`step=1` stay hard-coded, only `value`/`max` become Var-driven, and the text
readout is replaced by the new computed caption):

```python
def horizon_control() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Granularity", font_weight=FONT_WEIGHT_SEMIBOLD, size=RADIX_SIZE_BODY),
            rx.segmented_control.root(
                rx.segmented_control.item("Monthly", value="monthly"),
                rx.segmented_control.item("Weekly", value="weekly"),
                value=DashboardState.granularity,
                on_change=DashboardState.set_granularity,
                size="2",
                color_scheme="blue",
            ),
            spacing="2",
            align="center",
        ),
        rx.hstack(
            rx.text("Forecast horizon", font_weight=FONT_WEIGHT_SEMIBOLD, size=RADIX_SIZE_BODY),
            rx.slider(
                value=[DashboardState.active_horizon],
                min=1,
                max=DashboardState.horizon_max,
                step=1,
                on_change=DashboardState.set_horizon,
                size="2",
                width="100%",
                max_width="15rem",
                color_scheme="blue",
            ),
            rx.text(DashboardState.horizon_caption, size=RADIX_SIZE_BODY),
            align="center",
            spacing="2",
            wrap="wrap",
        ),
        spacing="2",
        wrap="wrap",
    )
```

**MEDIUM confidence flag:** `rx.slider`'s `max` prop being bound to a reactive `rx.Var`
(rather than a static int, as it is today at `app.py:293`) was not independently verified
against Reflex's own docs/Context7 this session — no MCP Context7 tool was available in
this environment. Every other numeric prop already Var-bound elsewhere in this app
(`value=[DashboardState.horizon_months]` itself, `card["base"]` text, etc.) works, and
Radix's underlying `Slider.Root` accepts `max` as a controlled prop with no documented
restriction against dynamic values, so this is expected to work, but the executor should
smoke-test dragging the slider immediately after switching to Weekly mode (does the
thumb's draggable range actually update, or does it require a re-mount?) before relying
on it — flagged in Assumptions Log as A1.

---

### Pattern 3: Diesel card dimming (WKUI-05)

**Requirement/app mismatch (read this first):** WKUI-05 says "Diesel-USD and Diesel-MNT
cards," but `SUMMARY_CARD_SERIES = ("hdan", "ppan", "diesel_mnt", "fx_rate")`
(`state.py:122`) — **there is no Diesel-USD summary card today.** Its docstring is
explicit about why: *"Deliberately excludes diesel_usd_ton from FORECAST_SERIES_LABELS'
five keys because the user tracks the MNT purchasing price (diesel_mnt), not the raw
USD/ton input"* (`state.py:118-121`). So:
- **Diesel-MNT**: dim the existing summary card (Summary tab) — this is a direct,
  unambiguous match to WKUI-05.
- **Diesel-USD**: has no card to dim. Its honest "monthly only" surface must be the
  Forecast tab's series selector + forecast table column set instead (see Pattern 6/7).
  This is a genuine design-interpretation decision, not something CONTEXT.md resolved —
  flagged as Open Question 1 below; the plan should explicitly record this mapping so a
  human verifier checking WKUI-05 knows where to look for Diesel-USD's honest state.

**`theme.py` addition** (theme.py currently has no disabled/dimmed-opacity token — its
own file docstring states the goal is "no scattered literals," so this new constant
belongs here, not as a bare string in `app.py`):

```python
# ---------------------------------------------------------------------------
# Disabled/muted-state opacity (Phase 22 — WKUI-05 Diesel "monthly only" dim)
# Cross-mode (not per light/dark, like CARD_RADIUS/SPACE_* above) since
# opacity is a multiplier, not a color — the same value reads correctly
# against either SURFACE token.
# ---------------------------------------------------------------------------
DIMMED_OPACITY = "0.55"
```

**`state.py`'s `summary_cards` branching** — every dict entry (both the `has_data == "no"`
branch and the `has_data == "yes"` branch, per the file's existing "Phase 6 flat-dict
discipline" comment at `state.py:571`) gains two new keys, `is_dimmed` and
`cadence_badge`, using the same all-string convention as `has_data`:

```python
WEEKLY_CAPABLE_SERIES: frozenset[str] = frozenset({"hdan", "ppan", "fx_rate"})

# inside the summary_cards loop, before building each card dict:
is_weekly_capable = key in WEEKLY_CAPABLE_SERIES
use_weekly = self.granularity == "weekly" and is_weekly_capable
is_dimmed = "yes" if (self.granularity == "weekly" and not is_weekly_capable) else "no"
cadence_badge = "Monthly data only" if is_dimmed == "yes" else ""
```
...then add `"is_dimmed": is_dimmed, "cadence_badge": cadence_badge` to both the no-data
and has-data dict literals (`state.py:641-663` and `693-716`).

**`app.py`'s `_summary_card()` rendering** — apply the dim opacity to the *value content
only*, not the label/badge, so the badge stays legible while the numbers read as visibly
muted (this matches CONTEXT's "small badge/label explaining... with the dimmed monthly
numbers" wording — the badge itself should not be dimmed, only the numeric content
around it):

```python
from app.theme import DIMMED_OPACITY  # add to the existing theme import block

# inside _summary_card(), directly under the existing card["label"] rx.text:
rx.cond(
    card["cadence_badge"] != "",
    rx.text(
        card["cadence_badge"],
        size=RADIX_SIZE_LABEL,
        color=DashboardState.muted_text,
        font_weight=FONT_WEIGHT_SEMIBOLD,
    ),
    rx.fragment(),
),
# then wrap the EXISTING has_data rx.cond's true-branch rx.fragment(...) in:
rx.box(
    <existing has_data-true rx.fragment(...) contents unchanged>,
    opacity=rx.cond(card["is_dimmed"] == "yes", DIMMED_OPACITY, "1"),
),
```

Grid position is untouched — `forecast_summary_cards()`'s `rx.foreach(DashboardState.summary_cards, _summary_card)` (`app.py:591`) keeps rendering exactly 4 cards in the same order regardless of granularity, satisfying "stays in its normal grid position."

---

### Pattern 4: Provenance line branching (WKUI-07)

**Existing pattern** (`state.py:632-638`):
```python
model_label = "Model"
model_name, model_mape = MODEL_INFO[key]
if model_mape is None:
    model_text = model_name
else:
    model_text = f"{model_name} · {model_mape:.1f}% typical error"
```

**Recommended branch**, replacing the block above inside the `summary_cards` loop:
```python
model_label = "Model"
if use_weekly:
    # [CONTINGENT ON PHASE 21]: WEEKLY_MODEL_INFO's exact tuple shape --
    # 21-CONTEXT.md/21-RESEARCH.md specify dict[str, tuple[str, float]],
    # no None-mape case (unlike monthly MODEL_INFO's diesel_mnt entry) --
    # verify at implementation time.
    weekly_name, weekly_mape = WEEKLY_MODEL_INFO[key]
    monthly_name, monthly_mape = MODEL_INFO[key]
    # Should-have (FEATURES.md): fold the accuracy delta into the same
    # line rather than a separate widget.
    if monthly_mape is not None:
        model_text = f"{weekly_name} · {weekly_mape:.2f}% MAPE weekly · {monthly_mape:.1f}% monthly"
    else:
        model_text = f"{weekly_name} · {weekly_mape:.2f}% MAPE weekly"
else:
    model_name, model_mape = MODEL_INFO[key]
    model_text = model_name if model_mape is None else f"{model_name} · {model_mape:.1f}% typical error"
```

This only ever executes the weekly branch for `key in WEEKLY_CAPABLE_SERIES` (guarded by
`use_weekly` from Pattern 3), so `diesel_mnt`'s provenance line is untouched in Weekly
mode — it still reads `MODEL_INFO["diesel_mnt"]` (the `"Derived (Diesel USD × FX ÷ 1,136
L)"` string with `mape=None`), which is correct: Diesel's card is dimmed, not swapped to
a fake weekly model.

---

### Pattern 5: Data source branching for `summary_cards` (WKUI-03)

Full sketch of how Pattern 3 and Pattern 4 slot into the existing loop
(`state.py:568-717`), showing exactly what changes vs. what's untouched:

```python
@rx.var
def summary_cards(self) -> list[dict[str, str]]:
    results = self.forecast_results          # UNCHANGED — monthly, always computed
    weekly_results = self.weekly_forecast_results  # NEW — see Pattern 8
    cards: list[dict[str, str]] = []

    for key in SUMMARY_CARD_SERIES:           # UNCHANGED: hdan, ppan, diesel_mnt, fx_rate
        label = FORECAST_SERIES_LABELS[key]
        is_weekly_capable = key in WEEKLY_CAPABLE_SERIES
        use_weekly = self.granularity == "weekly" and is_weekly_capable
        series = weekly_results.get(key, []) if use_weekly else results.get(key, [])

        # hilo_text / yoy_text: UNCHANGED, still sourced from
        # self._actual_series_for(key) (monthly PriceRow actuals) even in
        # Weekly mode -- see Open Question 2 for why this is the
        # recommended MVP choice, not an oversight.
        ...

        # model_text: Pattern 4's branch, using `use_weekly`
        ...

        is_dimmed = "yes" if (self.granularity == "weekly" and not is_weekly_capable) else "no"
        cadence_badge = "Monthly data only" if is_dimmed == "yes" else ""

        if not series:
            cards.append({..., "is_dimmed": is_dimmed, "cadence_badge": cadence_badge})
            continue

        entry = series[-1]
        ... # base/bull/bear/direction math UNCHANGED, just reading from `series`
        cards.append({..., "is_dimmed": is_dimmed, "cadence_badge": cadence_badge})

    return cards
```

Key point: **`use_weekly` only ever chooses which pre-computed dict to read (`results`
vs. `weekly_results`) and which model-info constant to read** — every downstream
base/bull/bear/direction/arrow computation is the exact same code path for both modes,
because both `forecast_all` and `forecast_all_weekly` are contracted to return the same
`{"base": ..., "bull": ..., "bear": ...}`-shaped per-entry dicts (per 21-CONTEXT.md's
explicit "same return contract" decision). This is what "no separate weekly card
component" (per the research question's constraint) looks like concretely.

---

### Pattern 6: Forecast chart branching (WKUI-03, WKUI-08)

**Series selector restriction:** rather than letting the user select Diesel-USD/Diesel-MNT
in the chart's `Series` dropdown while Weekly is active (which would force a choice
between silently showing stale monthly data under a "weekly" heading, or a second
in-chart badge system), restrict the dropdown's available options and auto-fallback the
selection (already wired in Pattern 1's `set_granularity`). This is the one point where
this phase's recommendation *diverges* from the literal "always show Diesel, dimmed"
card treatment — because the chart is a single-series-at-a-time view (not an
always-all-visible grid), narrowing its options is a different, and arguably cleaner,
honesty mechanism than dimming a chart the user explicitly picked to view. Flagged as
Open Question 3 for planner sign-off (CONTEXT.md's locked decision only specifies card
treatment, not chart-selector treatment).

```python
WEEKLY_FORECAST_SERIES_LABELS: dict[str, str] = {
    "hdan": "HDAN",
    "ppan": "PPAN",
    "fx_rate": "FX Rate",
}

@rx.var
def available_forecast_series_labels(self) -> list[str]:
    """Options list for the Series select — narrows to weekly-capable
    series while granularity == 'weekly' (Pattern 6 rationale above)."""
    if self.granularity == "weekly":
        return list(WEEKLY_FORECAST_SERIES_LABELS.values())
    return list(FORECAST_SERIES_LABELS.values())
```
`forecast_chart()` in `app.py` swaps its `rx.select(list(FORECAST_SERIES_LABELS.values()), ...)` (`app.py:391`) for `rx.select(DashboardState.available_forecast_series_labels, ...)`.

**Chart figure branching** (`forecast_chart_figure`, `state.py:753-878`) — top-of-function
branch, reusing every downstream trace-building line unchanged by building the same four
local variables (`series`, `hist_dates`, `hist_values`/`hist_dates_dt`, `fc_dates`) from a
weekly source instead of a monthly one:

```python
@rx.var
def forecast_chart_figure(self) -> go.Figure:
    t = tokens(self.theme_mode)
    attr = self.forecast_series
    use_weekly = self.granularity == "weekly"

    if use_weekly:
        results = self.weekly_forecast_results
        series = results.get(attr, [])
        hist_pairs = self._weekly_actual_series_for(attr)[-12:]  # NEW helper, Pattern 8
    else:
        results = self.forecast_results
        series = results.get(attr, [])
        hist_pairs = self._actual_series_for(attr)[-12:]         # UNCHANGED

    hist_dates: list = [d for d, _ in hist_pairs]
    hist_values: list = [v for _, v in hist_pairs]

    if not series or not hist_dates:
        ... # UNCHANGED empty-state figure, just update yaxis_title source below

    hist_dates_dt = pd.to_datetime(hist_dates).tolist()
    last_hist_date = hist_dates_dt[-1]
    last_hist_value = hist_values[-1]

    # [CONTINGENT ON PHASE 21]: entry["month"] is a generic 1-indexed STEP
    # NUMBER, not a literal calendar month -- forecast_all's _to_rows
    # helper names the key "month" but it's really "h" (see forecasting.py
    # _to_rows, line ~526-539). Phase 21's forecast_all_weekly almost
    # certainly reuses the SAME _to_rows helper unchanged (21-RESEARCH.md
    # doesn't propose renaming it), so this key will still be called
    # "month" even for weekly entries -- verify this at implementation
    # time rather than assuming a "week" key exists.
    offset_unit = "weeks" if use_weekly else "months"
    fc_dates = [
        last_hist_date + pd.DateOffset(**{offset_unit: entry["month"]})
        for entry in series
    ]
    fc_base = [entry["base"] for entry in series]
    fc_bull = [entry["bull"] for entry in series]
    fc_bear = [entry["bear"] for entry in series]

    # ... bridge_dates / figure trace-building: UNCHANGED from here down
```

This satisfies WKUI-08 "real week-ending dates" because `hist_dates`/`last_hist_date`
now come from `WeeklyPriceRow.date` (Phase 19's already-merged real dates — see Pitfall 2
below for why no additional AN-vs-FX alignment work is needed here), and `fc_dates`
offsets forward in real calendar weeks rather than months.

---

### Pattern 7: Forecast table branching (WKUI-03, WKUI-08)

`forecast_table_rows` (`state.py:880-904`) currently emits `{"month": str(month), ...}`
where `month` is a bare 1-indexed integer string ("1", "2", "3"...) — **not** a real
calendar date, even in today's monthly-only shipped behavior. So WKUI-08's "real
week-ending dates... not relabeled monthly tick marks" is best satisfied by computing an
actual date string for the weekly branch (something the monthly table has never needed
to do), rather than just swapping "Month" for "Week" as a header relabel — a bare "Week
1"/"Week 2" would itself be exactly the kind of "relabeled tick" WKUI-08 is written to
rule out.

```python
WEEKLY_FORECAST_TABLE_COLUMNS: list[tuple[str, str]] = [
    (f"{series_key}_{scenario}", f"{label} {scenario}")
    for series_key, label in WEEKLY_FORECAST_SERIES_LABELS.items()
    for scenario in ("base", "bull", "bear")
]

@rx.var
def forecast_table_rows(self) -> list[dict[str, str]]:
    if self.granularity == "weekly":
        results = self.weekly_forecast_results
        if not any(results.get(key) for key in WEEKLY_FORECAST_SERIES_LABELS):
            return []
        weekly_hist = self._weekly_actual_series_for("hdan")  # any weekly-capable key's dates align (Phase 19 pre-merged)
        if not weekly_hist:
            return []
        last_date = pd.to_datetime(weekly_hist[-1][0])
        rows: list[dict[str, str]] = []
        for step in range(1, self.horizon_weeks + 1):
            week_date = last_date + pd.DateOffset(weeks=step)
            row: dict[str, str] = {"month": week_date.strftime("%Y-%m-%d")}  # key name "month" kept for template/component reuse -- see below
            for series_key in WEEKLY_FORECAST_SERIES_LABELS:
                series = results.get(series_key, [])
                entry = series[step - 1] if step - 1 < len(series) else None
                for scenario in ("base", "bull", "bear"):
                    value = entry[scenario] if entry is not None else None
                    row[f"{series_key}_{scenario}"] = f"{value:,.2f}" if value is not None else ""
            rows.append(row)
        return rows

    # UNCHANGED monthly branch below (existing state.py:888-904 body, verbatim)
    ...
```

`row["month"]`'s key name is deliberately kept as `"month"` even for weekly rows (rather
than introducing a `"week"` key) so `app.py`'s `forecast_table()` can render the first
column with `row["month"]` unconditionally — only the header label and the column *set*
(`WEEKLY_FORECAST_TABLE_COLUMNS` vs. `FORECAST_TABLE_COLUMNS`) need to branch, not every
per-row key name. `forecast_table()`'s header/column-set branch:

```python
def forecast_table() -> rx.Component:
    def _table(columns, first_header):
        return rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(first_header),
                    *[rx.table.column_header_cell(label) for _, label in columns],
                )
            ),
            rx.table.body(
                rx.foreach(
                    DashboardState.forecast_table_rows,
                    lambda row: rx.table.row(
                        rx.table.cell(row["month"], font_family="'IBM Plex Mono', monospace"),
                        *[rx.table.cell(row[key], font_family="'IBM Plex Mono', monospace") for key, _ in columns],
                    ),
                )
            ),
        )

    table = rx.cond(
        DashboardState.granularity == "weekly",
        _table(WEEKLY_FORECAST_TABLE_COLUMNS, "Week of"),
        _table(FORECAST_TABLE_COLUMNS, "Month"),
    )
    # ... warning_banner / empty-state wrapper: UNCHANGED
```

Note: `rx.cond` branches must both be `rx.Component` trees (not plain Python `if`), and
`FORECAST_TABLE_COLUMNS`/`WEEKLY_FORECAST_TABLE_COLUMNS` are both plain Python constants
(not Vars) known at compile/render time, so passing them as ordinary Python arguments
into `_table(...)` inside each `rx.cond` branch is safe — this mirrors how
`csv_import_control()` already nests multiple `rx.cond` branches for `import_stage`
(`app.py:754-767`).

---

### Pattern 8: Weekly history loading (backing data for all of the above)

`DashboardState` has no `WeeklyPriceRow` reads today. Add a parallel var + loader,
mirroring `rows`/`load_rows()`/`_history_df()` exactly (`state.py:140`, `931-940`,
`917-929`):

```python
from app.models import AppSetting, PriceRow, WeeklyPriceRow  # add WeeklyPriceRow

WEEKLY_SERIES_ATTRS = ("hdan", "ppan", "baltic_an", "fx_rate")  # WeeklyPriceRow's 4 non-date columns

class DashboardState(rx.State):
    ...
    weekly_rows: list[WeeklyPriceRow] = []

    def load_weekly_rows(self) -> None:
        """Mirrors load_rows() exactly, for WeeklyPriceRow (Phase 19)."""
        with rx.session() as session:
            self.weekly_rows = session.exec(
                WeeklyPriceRow.select().order_by(WeeklyPriceRow.date)
            ).all()

    def _weekly_history_df(self) -> pd.DataFrame:
        """Mirrors _history_df() exactly, sourced from weekly_rows."""
        if not self.weekly_rows:
            return pd.DataFrame()
        records = [
            {attr: getattr(row, attr) for attr in WEEKLY_SERIES_ATTRS}
            for row in self.weekly_rows
        ]
        index = pd.DatetimeIndex(pd.to_datetime([row.date for row in self.weekly_rows]))
        return pd.DataFrame(records, index=index).sort_index()

    def _weekly_actual_series_for(self, key: str) -> list[tuple[str, float]]:
        """Mirrors _actual_series_for() exactly, but WeeklyPriceRow has no
        diesel_mnt-style derived key -- only ever called with
        key in WEEKLY_CAPABLE_SERIES."""
        pairs: list[tuple[str, float]] = []
        for row in self.weekly_rows:
            value = getattr(row, key)
            if value is None:
                continue
            pairs.append((row.date, value))
        return pairs

    @rx.var
    def weekly_forecast_results(self) -> dict:
        """Mirrors forecast_results exactly (state.py:475-506) -- the
        SAME "exactly one call site" discipline applies here,
        independently: this is the ONE place forecast_all_weekly is
        called, just as forecast_results is the one place forecast_all
        is called. [CONTINGENT ON PHASE 21] for forecast_all_weekly's
        exact signature/exception types."""
        empty_result = {key: [] for key in WEEKLY_FORECAST_SERIES_LABELS}
        if not self.weekly_rows:
            self.weekly_forecast_error = (
                "Not enough weekly historical data to forecast yet."
            )
            return empty_result
        history = self._weekly_history_df()
        try:
            result = forecast_all_weekly(history, self.horizon_weeks)
        except (InsufficientHistoryError, ValueError):
            self.weekly_forecast_error = (
                "Not enough weekly historical data to forecast yet."
            )
            return empty_result
        self.weekly_forecast_error = ""
        return result
```

`weekly_forecast_error: str = ""` needs declaring alongside `forecast_error` near the top
of `DashboardState`. `index()`'s `on_mount` list (`app.py:927`) gains
`DashboardState.load_weekly_rows` alongside the existing `load_rows`/`load_markup_pct`.

### Anti-Patterns to Avoid

- **Building a second, parallel `weekly_summary_cards()`/`weekly_forecast_chart_figure()`
  component/var pair.** The research question explicitly rules this out ("must NOT
  require two separate page/component trees, just conditional data sourcing"), and every
  pattern above is written to satisfy that — one function, one component, an internal
  branch on `self.granularity`.
- **Sharing `horizon_months` between modes** — see Pattern 2's rationale; this would
  either violate the "Monthly pixel-identical" regression constraint or add extra
  reset/re-clamp state-transition surface with no benefit.
- **Fabricating a weekly Diesel value** (e.g. flat-repeating the last monthly Diesel
  forecast across weekly x-axis ticks) — explicitly forbidden by PITFALLS.md Pitfall 5
  and the locked CONTEXT decision; this phase's design deliberately never calls a weekly
  forecast function for `diesel_usd_ton`/`diesel_mnt` because Phase 21 doesn't produce one.
- **Applying the dim `opacity` to the whole card box including the badge text** — makes
  the explanatory badge itself hard to read, undermining the point of adding it. Dim only
  the value-content subtree (Pattern 3).
- **Assuming `entry["month"]` is a real calendar-month offset for weekly rows.** It's a
  generic step index reused from `_to_rows` — treat it as `h`, not as a semantic month
  count (Pattern 6/7).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Toggle persistence | A new `AppSetting`-DB-row-backed toggle, or a hand-rolled cookie | `rx.LocalStorage("monthly", name="pd_granularity")` | Exact mechanism `theme_mode` already proved works and persists correctly (Phase 11); CONTEXT.md explicitly locks reusing it. |
| Two-state selectable control | Hand-rolled `rx.hstack` of two `rx.button`s with manual active-state styling | `rx.segmented_control.root`/`.item` | Radix/Reflex already ships the exact single-select interaction with ARIA wiring for free — `nav_bar()`'s own docstring already established this "don't hand-roll what Radix ships" precedent in this codebase for tabs. |
| Weekly model spread/provenance numbers | Recomputing MAPE or re-deriving model choice in `state.py` | `WEEKLY_MODEL_INFO`/`forecast_all_weekly` from Phase 21's `forecasting.py` | This project's standing discipline (CLAUDE.md: "no un-backtested model ships to the dashboard") — `state.py` must only ever read Phase 21's frozen constants/dispatcher, never fit a model or pick a MAPE number itself. |
| Weekly date alignment (AN-family Friday vs. FX Monday convention) | A new `merge_asof`/tolerance-join call inside `state.py` | `WeeklyPriceRow.date` as-is | Phase 19 already solved this upstream — `WeeklyPriceRow` stores one already-tolerance-merged date per row spanning hdan/ppan/baltic_an/fx_rate (confirmed: `models.py`'s `WeeklyPriceRow` has a single shared `date` field, and ROADMAP.md's Phase 19 success criterion #4 explicitly required the `merge_asof` join before ingestion). Phase 22 should never re-join or re-align weekly dates itself. |

**Key insight:** every piece of this phase that looks like it needs new logic
(persistence, model-selection UI, date alignment) is actually a "read what an earlier
phase already built correctly" problem, not a "build something new" problem. The only
genuinely new code is glue: branching existing render functions on one new state var.

## Common Pitfalls

### Pitfall 1: Sharing `horizon_months` across granularity modes
**What goes wrong:** A shared/reused horizon var either silently reinterprets a
weekly-mode value as months (or vice versa) on toggle flip, or requires ad-hoc
reset/clamp logic on every `set_granularity` call that isn't otherwise needed.
**Why it happens:** `set_horizon`'s existing clamp is hard-coded to `MAX_HORIZON`
(`state.py:522`); it's tempting to just widen that clamp conditionally rather than add a
whole second var.
**How to avoid:** Use the separate `horizon_weeks` var + `active_horizon`/`horizon_max`
computed-var pair from Pattern 2.
**Warning signs:** Any single `horizon_months` int field being read by both
`forecast_results` and `weekly_forecast_results`.

### Pitfall 2: Re-deriving AN-vs-FX weekly date alignment inside `state.py`
**What goes wrong:** Re-implementing the `merge_asof` tolerance join PITFALLS.md's
Pitfall 4 warned about, inside Phase 22's UI code, duplicating work Phase 19 already did.
**Why it happens:** PITFALLS.md's milestone-level research (written before Phase 19
shipped) flagged this as a live risk; it's easy to over-defensively re-solve it here
without checking that Phase 19 already closed it.
**How to avoid:** Trust `WeeklyPriceRow.date` as a single, already-aligned date per row
(confirmed via `models.py` and ROADMAP.md's Phase 19 success criteria) — never join
`WeeklyPriceRow` against itself or against `PriceRow` by date in this phase's code.
**Warning signs:** Any new `pd.merge_asof`/`pd.merge` call appearing in `state.py`.

### Pitfall 3: WKUI-05's "Diesel-USD card" not existing in the shipped app
**What goes wrong:** A plan/task literally titled "dim the Diesel-USD summary card"
would be un-executable as written, since `SUMMARY_CARD_SERIES` never included
`diesel_usd_ton` (state.py:118-122, by deliberate prior design).
**Why it happens:** WKUI-05's requirement text was written against the milestone's
general intent, not against a line-by-line audit of `SUMMARY_CARD_SERIES`.
**How to avoid:** Interpret WKUI-05 as covering (a) the Diesel-MNT summary card
(dimmed, per Pattern 3) and (b) the Forecast tab's Diesel-USD-USD/-MNT presence via the
series selector + table column restriction (Pattern 6/7) — record this mapping
explicitly in the phase's plan and human-verification checklist so a reviewer checking
WKUI-05 against the shipped app knows both surfaces satisfy it.
**Warning signs:** A plan task that can't find a `diesel_usd_ton` entry in
`SUMMARY_CARD_SERIES` to modify.

### Pitfall 4: Dead/invalid `forecast_series` selection after toggling to Weekly
**What goes wrong:** If the user has "Diesel USD/t" or "Diesel MNT/L" selected in the
Forecast tab's chart when they flip to Weekly, and nothing resets `forecast_series`, the
chart either renders empty (no weekly Diesel data exists) or the dropdown shows a label
no longer present in the narrowed options list (`available_forecast_series_labels`),
producing a Radix console warning for an out-of-range `value`.
**Why it happens:** `forecast_series` and `granularity` are otherwise fully independent
state vars with no coupling by default.
**How to avoid:** `set_granularity`'s fallback (Pattern 1) — reset `forecast_series` to
`"hdan"` when switching to Weekly if the currently-selected series isn't weekly-capable.
**Warning signs:** Browser console warning about `rx.select`'s `value` prop not matching
any `rx.select.item`; an empty fan chart with "No forecast available" immediately after
toggling to Weekly.

### Pitfall 5: Card dict key-parity break (`is_dimmed`/`cadence_badge` missing from one branch)
**What goes wrong:** `summary_cards`' existing "Phase 6 flat-dict discipline" comment
(`state.py:571`) exists specifically because `app.py`'s `_summary_card()` indexes
`card["..."]` unconditionally — if the two new keys are added to only the `has_data ==
"yes"` branch (or only the `"no"` branch) and not both, the missing branch will raise a
Reflex Var-indexing error (or silently render `undefined`) the first time that branch is
hit.
**Why it happens:** The two branches are ~70 lines apart in the function
(`state.py:640-664` vs. `693-716`); it's easy to edit one and forget the other.
**How to avoid:** Compute `is_dimmed`/`cadence_badge` once, above the `if not series:`
branch point (as shown in Pattern 5's sketch), so both `cards.append(...)` calls
reference the same two already-computed local variables — impossible to add to one and
forget the other if both literals read from the same locals.
**Warning signs:** Works fine for series with data, breaks (or shows blank) specifically
for a series with `has_data == "no"` (e.g. before any weekly history is seeded/loaded).

### Pitfall 6 (restated from milestone PITFALLS.md, Pitfall 5 — most consequential): Monthly-only series mis-rendered in weekly mode
**What goes wrong:** Diesel silently disappears, shows fabricated weekly-looking points,
or throws when a weekly-mode code path assumes every series has weekly data.
**How to avoid:** Every pattern above (`summary_cards`, `forecast_chart_figure`,
`forecast_table_rows`) is built around `WEEKLY_CAPABLE_SERIES`/`use_weekly` guards that
explicitly branch Diesel to its existing monthly path, never a weekly one that doesn't
exist. This is the single most important acceptance-criterion to human-verify: toggle to
Weekly, confirm the Diesel-MNT card is visibly dimmed with a badge (not blank, not
missing, not showing a suspiciously-precise "weekly" number), and confirm the Forecast
tab's series dropdown doesn't offer a Diesel option that produces an empty/broken chart.

## Code Examples

### Reflex `rx.segmented_control` — confirmed current API
```python
# Source: https://reflex.dev/docs/library/disclosure/segmented-control/ [CITED, fetched 2026-09-01]
import reflex as rx

class SegmentedState(rx.State):
    selected: str = "inbox"

def segmented_example() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item("Inbox", value="inbox"),
        rx.segmented_control.item("Drafts", value="drafts"),
        value=SegmentedState.selected,
        on_change=SegmentedState.set_selected,
        size="2",
        variant="surface",
    )
```

### Existing `theme_mode` persistence pattern this phase mirrors
```python
# Source: app/app/state.py:216 (read directly, HIGH confidence)
theme_mode: str = rx.LocalStorage("light", name="pd_theme_mode")
```

## State of the Art

Not applicable in the usual sense (no external ecosystem drift risk here — this is
entirely internal-codebase pattern reuse). One internal note:

| Old Approach | Current Approach (this phase) | Impact |
|--------------|-------------------------------|--------|
| `forecast_table_rows`' "month" column is always a bare 1-indexed integer string, never a real date | Weekly branch computes and renders a real `YYYY-MM-DD` week-ending date string in the same key | First time this table has ever shown a genuine calendar date rather than a relative step index — monthly branch is unchanged, so this is additive only. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `rx.slider`'s `max` prop accepts a reactive `rx.Var` (not just a static literal) without requiring a remount/key-reset to pick up the new bound | Pattern 2 | MEDIUM — if wrong, dragging the slider after toggling to Weekly could stay clamped to the old (12) max, or the DOM slider could visually glitch. Not independently verified this session (no Context7/MCP access); other numeric Vars are already bound successfully elsewhere in this app (`value=[...]`), which is suggestive but not identical (`value` vs. `max`). Executor should smoke-test this specific interaction first. |
| A2 | `MAX_HORIZON_WEEKLY` (name), `WEEKLY_MODEL_INFO` (shape), and `forecast_all_weekly` (signature: `(history, horizon)`, no `markup_pct`) will land in Phase 21 exactly as named/shaped in 21-CONTEXT.md/21-RESEARCH.md | Patterns 2, 4, 8 | HIGH if wrong — every `[CONTINGENT ON PHASE 21]`-tagged code block in this document uses these exact names; if Phase 21 ships different names/shapes, this phase's plan must be re-verified against Phase 21's actual shipped `forecasting.py` before execution, not against this document. This is flagged prominently in the Summary section as well. |
| A3 | Restricting the Forecast tab's series dropdown (Pattern 6) rather than dimming a Diesel chart view is an acceptable interpretation of "never hidden, never faked" for the single-series chart context, distinct from the always-visible card grid | Pattern 6 | LOW-MEDIUM — this is presented as a recommendation, not a locked decision; CONTEXT.md's locked language is specific to "cards." If a human reviewer disagrees, the alternative (keep Diesel selectable, show a dimmed chart + banner) is a moderate rework of Pattern 6 only, isolated from every other pattern. |
| A4 | Historical high/low (`hilo_text`) and YoY (`yoy_text`) on weekly-mode summary cards should continue reading monthly `PriceRow` actuals (via the existing `_actual_series_for`), not a newly-sourced weekly-actuals equivalent | Pattern 5, Open Question 2 | LOW — WKUI-03..08 never requires weekly-sourced historical context stats, only weekly model name/MAPE (WKUI-07) and weekly forecast dates (WKUI-08). Keeping hi/lo & YoY monthly-sourced is cheaper and lower-risk, but a reviewer could reasonably want these cadence-matched too; flagged as an open question for planner sign-off. |

## Open Questions

1. **Where does "Diesel-USD... monthly only" actually surface, given no Diesel-USD
   summary card exists?**
   - What we know: `SUMMARY_CARD_SERIES` has 4 keys, only one of which (`diesel_mnt`) is
     Diesel-related; `diesel_usd_ton` only appears in the Forecast tab's series selector
     and table.
   - What's unclear: whether WKUI-05's acceptance criterion should be interpreted as
     "the Forecast tab's Diesel-USD/-MNT surfaces (selector + table columns) honestly
     degrade" (this document's recommendation, Pattern 6/7) or whether the phase should
     add a net-new Diesel-USD summary card just to have something to dim (scope
     expansion beyond what CONTEXT.md discussed).
   - Recommendation: go with the Pattern 6/7 interpretation (no new card) — adding a new
     card would be a bigger, unplanned UI change and CONTEXT.md's "Diesel-USD/Diesel-MNT
     cards stay in place" phrasing reads as describing today's (single, `diesel_mnt`)
     card, generalized loosely. Confirm with the user/planner if this reading is
     contested.

2. **Should Diesel-MNT's high/low and YoY figures on the dimmed weekly card continue
   reading monthly actuals, or should weekly-capable cards (HDAN/PPAN/FX) source their
   high/low and YoY from `WeeklyPriceRow` instead of `PriceRow` while in Weekly mode?**
   - What we know: neither WKUI-03..08 nor CONTEXT.md's locked decisions mention hi/lo or
     YoY at all — they're silent on this.
   - What's unclear: whether a user in Weekly mode would expect "All-time high/low" and
     "YoY" to reflect weekly-cadence history (which only goes back to Phase 19's ingested
     range, likely shorter than `PriceRow`'s full monthly history) or the existing
     full-history monthly figures (longer lookback, cadence-mismatched but arguably more
     informative).
   - Recommendation: keep these monthly-sourced for all cards regardless of granularity
     (Assumption A4) — cheapest, lowest-risk, and not required by any WKUI line item.
     Revisit only if a human verifier flags it as confusing during Phase 22's
     verification pass.

3. **Should the Forecast tab's chart restrict Diesel out of the series dropdown when
   Weekly is active (this document's Pattern 6 recommendation), or should Diesel stay
   selectable with a dimmed/bannered chart matching the card treatment more literally?**
   - What we know: CONTEXT.md's locked "grayed-out card" decision text is specific to
     "cards... in its normal grid position" — language that doesn't map cleanly onto a
     single-series chart view.
   - What's unclear: whether a reviewer would consider "removed from the dropdown"
     equivalent-in-spirit to "never hidden" (PITFALLS.md's stated principle) since the
     option is still visibly present-but-disabled in one framing, or absent in another,
     depending on implementation.
   - Recommendation: implement the disabled-but-visible dropdown-item variant if Reflex's
     `rx.select.item` supports a `disabled` prop cleanly (not independently verified this
     session) — this reads as "visibly unavailable" rather than "silently removed,"
     better matching the honesty principle while still avoiding a second dimmed-chart
     rendering path. If `disabled` support turns out awkward, fall back to the simpler
     narrowed-list approach in Pattern 6 and note the tradeoff in the plan.

## Environment Availability

No new external tools/runtimes/services — this phase adds zero new dependencies (see
Standard Stack). The only real "environment" gap is a **phase dependency, not a tooling
gap**: Phase 21 has not shipped yet (verified: `app/app/forecasting.py` contains no
weekly symbols as of this research session). This phase's plan can be drafted against the
contracts documented in 21-CONTEXT.md/21-RESEARCH.md, but every `[CONTINGENT ON PHASE
21]`-tagged item in this document must be re-verified against Phase 21's actual shipped
`forecasting.py` (exact constant/function names, exact `MAX_HORIZON_WEEKLY` value, exact
`WEEKLY_MODEL_INFO` tuple shape) before this phase is executed, not merely before it is
planned.

## Security Domain

`security_enforcement` is not separately configured in `.planning/config.json` (absent =
enabled per the default). This phase's ASVS surface is minimal — it's a UI toggle over
already-validated, already-fitted forecast data, with no new user-supplied text input, no
new auth/session surface, and no new external network call.

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | App is single-user, no auth system exists or is being added. |
| V3 Session Management | No | No new session/cookie mechanics beyond Reflex's existing `rx.LocalStorage`/state session, unchanged pattern from `theme_mode`. |
| V4 Access Control | No | No new access boundary. |
| V5 Input Validation | Yes (narrow) | `set_granularity`'s allowlist check (`value not in ("monthly", "weekly")` → ignore) is the only new user-controlled input this phase introduces — mirrors the existing `select_series`/`select_forecast_series` "ignore unknown label" guard pattern already used throughout `state.py`. No open-ended string ever reaches a DB query or f-string used for anything beyond display text. |
| V6 Cryptography | No | Not applicable. |

No new threat patterns beyond what the existing shipped app already carries (single-user,
local SQLite, no network-exposed write surface beyond the existing Data Entry/CSV-import
paths, both untouched by this phase).

## Sources

### Primary (HIGH confidence)
- `app/app/app.py` (full file, 940 lines, read directly this session) — `horizon_control()`, `_summary_card()`, `forecast_chart()`, `forecast_table()`, `nav_bar()`, `theme_toggle()`, `index()`
- `app/app/state.py` (full file, 1224 lines, read directly this session) — `DashboardState`, `theme_mode`/`active_section` persistence patterns, `summary_cards`, `forecast_chart_figure`, `forecast_table_rows`, `forecast_results`, `_actual_series_for`, `_history_df`, `load_rows`
- `app/app/theme.py` (full file, read directly this session) — token structure, confirmed no existing dimmed/disabled opacity token
- `app/app/forecasting.py` (full file, 594 lines, read directly this session) — confirmed zero weekly symbols exist as of 2026-09-01; existing monthly `MODEL_INFO`/`forecast_all`/`MAX_HORIZON` pattern this phase's weekly consumers must mirror
- `app/app/models.py` (full file, read directly this session) — `WeeklyPriceRow` schema (single shared `date` column across hdan/ppan/baltic_an/fx_rate)
- `.planning/phases/22-weekly-granularity-toggle-ui/22-CONTEXT.md` — locked decisions
- `.planning/phases/21-weekly-forecasting-module/21-CONTEXT.md` and `21-RESEARCH.md` — Phase 21's proposed (not yet shipped) contract this phase depends on
- `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` — WKUI-03..08 text, Phase 19/20/21 success criteria
- `.planning/research/FEATURES.md`, `.planning/research/PITFALLS.md` — milestone-level research, especially Pitfall 5 (restated as this document's Pitfall 6)
- `.planning/config.json` — confirmed `workflow.nyquist_validation: false` (Validation Architecture section correctly omitted)

### Secondary (MEDIUM confidence)
- [Segmented Control · Reflex Docs](https://reflex.dev/docs/library/disclosure/segmented-control/) [CITED, fetched via WebFetch 2026-09-01] — confirmed `rx.segmented_control.root`/`.item` API surface (props, `on_change`)

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, `rx.segmented_control` confirmed via official docs this session
- Architecture (state/component wiring against existing shipped code): HIGH — every referenced line number/pattern was read directly from the actual files this session, not recalled from training data
- Architecture (anything touching Phase 21 names/shapes): MEDIUM-LOW, explicitly flagged `[CONTINGENT ON PHASE 21]` throughout — Phase 21 has not shipped as of this research
- Pitfalls: HIGH — each grounded in a specific line/behavior read directly from this repo's own code, plus one restated milestone-level pitfall already validated at the roadmap level

**Research date:** 2026-09-01
**Valid until:** Re-verify Phase 21-contingent sections immediately upon Phase 21 completion (not a time-based expiry — this research is stable until that specific dependency resolves); non-contingent sections (Patterns 1, 2's non-name parts, 3, 5's structure, 6's structure, 7's structure, 8's structure) are stable indefinitely against the current shipped codebase.
