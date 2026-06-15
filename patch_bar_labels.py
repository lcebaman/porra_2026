#!/usr/bin/env python3
"""Make the numbers inside stacked bars readable on every segment colour.

Root cause: the in-bar number has class="axis", and CSS `.axis{fill:var(--chalk-dim)}`
overrides any fill="..." attribute (in SVG, a stylesheet rule beats a presentation
attribute). The fix is an inline style="fill:..." , which wins the cascade. Each
number picks near-black or near-white from the brightness of its segment.

Only the centered label inside hBarStacked is touched; labels on the dark panel
background (totals, round-chart values) are left light on purpose.

Usage:  python patch_bar_labels.py porra_mundial_2026.html
Writes a .bak backup. Safe to re-run.
"""
import re, sys
from pathlib import Path

HELPER_ANCHOR = 'const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");'
HELPER = HELPER_ANCHOR + (
    "\n// Readable label colour for text drawn on top of a coloured fill `hex`.\n"
    "const txtOn=hex=>{const h=String(hex).replace('#','');"
    "const r=parseInt(h.slice(0,2),16),g=parseInt(h.slice(2,4),16),b=parseInt(h.slice(4,6),16);"
    "return (0.299*r+0.587*g+0.114*b)>140?'#08130e':'#f1f5f2';};"
)

FUNC_RE = re.compile(r'function hBarStacked\([^)]*\)\{.*?\n\}', re.DOTALL)

# the centered in-bar label (value ${v}, text-anchor middle) within hBarStacked
CENTERED_RE = re.compile(
    r'<text class="axis"((?: [a-z-]+="[^"]*")*?) text-anchor="middle"'
    r'(?:\s+fill="[^"]*")?(?:\s+style="[^"]*")?(?:\s+font-weight="700")?>'
    r'\$\{v\}</text>'
)

def centered_sub(m):
    return (f'<text class="axis"{m.group(1)} text-anchor="middle" '
            f'style="fill:${{txtOn(segs[k].color)}}" font-weight="700">${{v}}</text>')

def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1])
    doc = path.read_text(encoding="utf-8")

    fm = FUNC_RE.search(doc)
    if not fm:
        raise SystemExit(f"{path.name}: hBarStacked function not found.")
    body = fm.group(0)
    new_body, n = CENTERED_RE.subn(centered_sub, body)
    if n == 0:
        raise SystemExit(f"{path.name}: centered in-bar label not found in hBarStacked. "
                         f"Upload the file and I'll adjust the matcher.")
    if n != 1:
        raise SystemExit(f"{path.name}: expected exactly 1 centered label, found {n}. Aborting.")

    new = doc
    if "const txtOn=" not in new:
        if HELPER_ANCHOR not in new:
            raise SystemExit(f"{path.name}: esc() helper not found to anchor on.")
        new = new.replace(HELPER_ANCHOR, HELPER, 1)
    new = new.replace(body, new_body, 1)

    if new == doc:
        raise SystemExit(f"{path.name}: already patched — nothing to do.")
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(doc, encoding="utf-8")
    path.write_text(new, encoding="utf-8")
    print(f"Patched {path.name}: in-bar numbers now use an inline adaptive colour "
          f"(backup: {backup.name}).")

if __name__ == "__main__":
    main()
