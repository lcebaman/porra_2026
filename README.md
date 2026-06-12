# Porra Mundial 2026 — Prediction Pool Toolkit

Two pieces, one workflow:

| File | Role |
|---|---|
| `porra_mundial_2026.html` | Self-contained dashboard. All participants' predictions are embedded; the master enters real results in the browser and every score, chart and ranking recalculates instantly. Works offline — just open it. |
| `gather_predictions.py` | Collector. Extracts predictions from the participants' Excel template files, validates them, and injects them into the dashboard. The only tool you need to add, refresh or remove participants. |

Scoring lives **only** in the dashboard's JavaScript. The Python side never computes points — it extracts, resolves each participant's predicted bracket, validates, and injects. One source of truth for the rules.

---

## Requirements

- Python 3.10+ with `openpyxl` (`pip install openpyxl`)
- A modern browser for the dashboard (no internet needed except for the optional in-browser "Añadir participantes" button, which fetches SheetJS from a CDN)

---

## Quick reference

```bash
# Collect every prediction file in a folder and update the dashboard
python gather_predictions.py ./user_excels --inject porra_mundial_2026.html

# Add one new participant (drop the file in the folder, or pass it directly)
python gather_predictions.py extra/Luis.xlsx --inject porra_mundial_2026.html

# Remove a participant (no Excel files needed)
python gather_predictions.py --remove Sito --inject porra_mundial_2026.html

# Extract only — write predictions.json, touch nothing else
python gather_predictions.py ./user_excels -o predictions.json
```

---

## Command-line options

```
usage: gather_predictions.py [-h] [-o OUTPUT] [--inject INJECT]
                             [--remove NAME] [--template TEMPLATE]
                             [inputs ...]
```

### `inputs` (positional, zero or more)

Folders and/or individual prediction files, freely mixed.

- A **folder** is scanned for `*.xlsx` / `*.xlsm`; Excel lock files (`~$...`) are skipped.
- A **file** is taken as-is.
- Duplicates (same file given twice, or via folder + path) are de-duplicated.
- The participant's name is the **file stem**: `Paco.xlsx` → participant `Paco`. Rename the file to rename the participant.
- May be omitted entirely when the run is removal-only (`--remove` + `--inject`).

### `-o, --output FILE` (default: `predictions.json`)

Where to write the extracted JSON payload — per-user resolved predictions for all 104 matches, Premios picks, and any validation warnings. This file is your audit trail of exactly what was read from each Excel; it is only written when at least one input file was processed.

### `--inject DASHBOARD.html`

Update the dashboard **in place**. The script locates the embedded `const DATA = {...}` block and performs a surgical merge:

- **Replaces or adds** each collected participant's predictions (`preds`) and Premios picks (`bonus`). Re-running with the same files is idempotent.
- **Preserves untouched**: the schedule, team list, every other participant's data, all HTML/CSS/JS, and any results the master has already entered (those live in the browser's localStorage, keyed by match number — regenerating the file never loses them).
- **Extends the player-name canonical map** for Premios picks (see *Name canonicalization* below).
- Writes a backup of the previous version next to the file: `DASHBOARD.html.bak`.

Fallback: if the target HTML has no `const DATA` block but contains a `<script id="payload" type="application/json">` element (the older generic dashboard), that block is replaced wholesale instead.

### `--remove NAME` (repeatable, requires `--inject`)

Remove a participant from the dashboard: deletes them from `users`, `preds` and `bonus`. Properties:

- **Repeatable**: `--remove Sito --remove Pepe` removes both in one run.
- **Exact match** against the name shown in the leaderboard. A name that doesn't exist aborts the run with the full participant list and a "did you mean…?" suggestion — nothing is modified.
- **Removal wins over re-adding**: if the removed participant's Excel is still among the inputs, their file is skipped with a note instead of silently re-importing them. (Still, tidy the folder so a later full re-collection doesn't bring them back.)
- Can run standalone with no input files at all.
- Real scores already entered are unaffected (they aren't stored per participant).
- Caveat: a participant added through the dashboard's **in-browser** "Añadir participantes" button lives in the saved-progress JSON, not in the HTML. After removing them with the script, save fresh progress and don't re-import an old progress file, or they will reappear.

### `--template WORKBOOK.xlsx`

Read the `AssignThird` best-third-place assignment table once from a designated template/master workbook instead of from each participant's file. Normally unnecessary — every distributed template contains the table — but useful if a participant's file has a corrupted or stripped `AssignThird` sheet, or to shave a little time on large collections.

### `-h, --help`

Standard help.

---

## What extraction does per file

For each participant the script:

1. Reads the 72 group-stage scores plus all knockout scores and penalty shoot-outs from the `World Cup` sheet (fixed cell map matching the template geometry).
2. Recomputes their **predicted bracket in Python** — group standings (pts / GD / GF / name tie-breakers), seeds `1A…2L`, best-thirds via the `AssignThird` combination table, and `W##` / `RU##` winner/runner-up chains — so knockout slots resolve to real team names even when Excel's cached formula values are missing.
3. Reads Premios picks (5 goleadores, Bota/Guante/Balón de Oro) from the `Premios` sheet; the predicted tournament winner is derived from their Final.
4. Validates and prints a per-user report:

   | Warning | Meaning |
   |---|---|
   | `group match(es) without a score` | Empty group predictions (listed by match number) |
   | `knockout match(es) without a score` | Empty knockout predictions |
   | `knockout draw(s) without penalty resolution` | A KO draw with no penalties — **their bracket cannot advance past it**, so later rounds stay empty |
   | `knockout slot(s) with unresolved team(s)` | A bracket slot whose team couldn't be determined |
   | `empty Premios picks: …` | Which award picks are blank |
   | `[FAIL] file: missing sheet '…'` | Not a valid prediction template; the file is skipped, the run continues |

Best moment to run this: when a friend submits their file, while they can still fix it.

---

## Name canonicalization (Premios)

Participants type player names freely, so the dashboard unifies them through a `players` map (canonical key → display name) and an `alias` map (typo → canonical key). During injection, any new name is resolved in this order:

1. **Already known** (as player or alias) → nothing to do.
2. **Full-name variant of an existing entry** (e.g. `Mikel Oyarzabal` where key `oyarzabal` exists) → auto-aliased.
3. **Close typo** of an existing player (difflib similarity ≥ 0.92, e.g. `Erling Halland`) → auto-aliased, reported as `(fuzzy)`.
4. **Genuinely new** → added to the map and reported as *"check for typos / add aliases if needed"*.

Review that last list after each merge; for a typo too mangled for fuzzy matching, add one line to the dashboard's `alias` map by hand (same mechanism as the existing `"kulian mbappe": "kylian mbappe"` entry).

---

## The dashboard

Open `porra_mundial_2026.html` in a browser. Tabs:

- **Clasificación** — live leaderboard (Partidos / Cruces / Pases / Premios / Total) plus the point system.
- **Resultados** — the master enters real scores here. Group fixtures are pre-filled; knockout slots get team dropdowns; penalty boxes appear automatically on KO draws. Everything recalculates on every keystroke.
- **Premios** — enter each picked player's tournament goals (names already unified) and the real award winners; matches against picks are flagged automatically. The champion comes from the Final.
- **Estadísticas** — nine charts: *La carrera por la porra* (cumulative points), *De dónde vienen los puntos*, *Aciertos en partidos jugados*, *Puntos por ronda*, *La montaña rusa* (rank evolution), *El campeón de cada uno* (consensus), *Ojo de halcón* (mean goal error), *Pases acertados por ronda*, and *Las sorpresas del torneo* (matches fewest people scored on).
- **Detalle por jugador** — full per-participant audit: every scored match, prediction vs reality with point tags, advancement hits and bonus breakdown.

Persistence: entered results auto-save to the browser's localStorage. Use **Guardar progreso / Cargar progreso** for an explicit JSON backup — do this before switching browser/computer or sharing the file. **Añadir participantes** can import an updated master workbook directly in the browser (needs internet once, for SheetJS); script-based injection is the preferred path.

### Scoring rules encoded

Exact score 4 · correct winner 2 · correct KO pairing (cruce) 3 — in knockouts the pairing must match for result/winner points · advancement per correct team: R32 2, R16 4, QF 6, SF 9, Final 13 · champion 18 · 1 pt per goal of each chosen goleador and of the Bota de Oro pick · Guante/Bota/Balón de Oro 7 each · third-place match awards no advancement points.

---

## Common workflows

**New participant joins** — drop `Nombre.xlsx` into `./user_excels`, then:
```bash
python gather_predictions.py ./user_excels --inject porra_mundial_2026.html
```

**A participant corrects their file** — same command; their data is replaced.

**Someone drops out**:
```bash
python gather_predictions.py --remove Nombre --inject porra_mundial_2026.html
```
(then delete `Nombre.xlsx` from the folder)

**Roll back a bad merge** — every `--inject` leaves `porra_mundial_2026.html.bak`; copy it back over the file. Only the immediately previous version is kept.

**Distribute an update** — send the friends the new HTML. Their browsers keep nothing important; all state that matters lives with the master.

---

## Troubleshooting

- **"missing sheet 'World Cup' / 'Matches'"** — wrong file (not the prediction template) or a renamed sheet. Fix the file; other inputs are unaffected.
- **Knockout teams blank for one user** — almost always an unresolved KO draw earlier in their bracket; the validation report names the exact match.
- **`--remove` says the name doesn't exist** — names are exact (file-stem) matches; copy it from the error's participant list or the leaderboard.
- **Dashboard shows old data after injection** — hard-refresh (Ctrl+F5); you're looking at a cached copy.
- **Scores vanished after opening the file elsewhere** — localStorage is per browser/computer. Restore with *Cargar progreso* from your JSON backup.
