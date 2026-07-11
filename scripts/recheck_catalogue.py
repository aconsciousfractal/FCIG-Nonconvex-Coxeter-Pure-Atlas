#!/usr/bin/env python3
"""Regenerate or byte-check the 82-row LaTeX catalogue from the public atlas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "artifacts" / "nonconvex_tile_atlas.json"
OUTPUT = ROOT / "paper" / "generated" / "atlas_catalogue.tex"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def render(rows):
    require(len(rows) == 82, "catalogue requires exactly 82 rows")
    require(len({row["row_id"] for row in rows}) == 82, "catalogue row IDs are not unique")
    lines = [
        r"\begingroup\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{longtable}{@{}rllrrrrcr@{}}",
        r"\caption{Canonical nonconvex atlas. Symbols are defined in the appendix text.}\label{tab:full-atlas}\\",
        r"\toprule",
        r"\# & mask & $k$ & $h$ & $c$ & $q$ & $s$ & hand & $o$\\",
        r"\midrule",
        r"\endfirsthead",
        r"\multicolumn{9}{c}{\tablename\ \thetable\ (continued)}\\",
        r"\toprule",
        r"\# & mask & $k$ & $h$ & $c$ & $q$ & $s$ & hand & $o$\\",
        r"\midrule",
        r"\endhead",
        r"\midrule\multicolumn{9}{r}{continued on next page}\\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]
    for row in rows:
        cover = row["cover_structure"]
        ambient = row["ambient_tile_congruence"]
        hand = "A" if ambient["chirality"] == "ACHIRAL" else "C"
        lines.append(
            f"{row['atlas_ordinal1']} & \\rowid{{{row['canonical_mask_hex']}}} & "
            f"{row['k']} & {cover['tile_stabilizer_size']} & "
            f"{cover['raw_cover_count']} & {cover['cover_orbit_count']} & "
            f"{cover['multiplier_orbit_count']} & {hand} & "
            f"{ambient['oriented_A4_congruence_class_count']}\\\\"
        )
    lines.extend([r"\end{longtable}", r"\endgroup", ""])
    return "\n".join(lines).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace the table with regenerated LF bytes")
    args = parser.parse_args()
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    rendered = render(atlas["rows"])
    if args.write:
        OUTPUT.write_bytes(rendered)
        print(f"CATALOGUE_REGENERATED {OUTPUT.relative_to(ROOT).as_posix()}")
    else:
        require(OUTPUT.is_file(), "catalogue output is missing")
        require(OUTPUT.read_bytes() == rendered, "catalogue is not byte-identical")
        print("CATALOGUE_BYTE_EXACT_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, ValueError, OSError) as exc:
        print(f"CATALOGUE_RECHECK_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
