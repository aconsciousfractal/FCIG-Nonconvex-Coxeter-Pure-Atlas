#!/usr/bin/env python3
"""Recheck frozen secondary artifacts, parent pins, and the complete row join."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_public_package.py"


def main():
    spec = importlib.util.spec_from_file_location("public_package_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the public package verifier")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    atlas = verifier.load("nonconvex_tile_atlas.json")
    contact = verifier.load("contact_obstructions.json")
    boundary = verifier.load("boundary_presentations.json")
    covers = verifier.load("cover_atlas.json")
    ambient = verifier.load("ambient_symmetry_atlas.json")
    gate = verifier.load("global_congruence_gate.json")
    verifier.verify_frozen_secondary_artifacts(
        atlas, contact, boundary, covers, ambient, gate
    )
    print("FROZEN_SECONDARY_ARTIFACT_RECHECK_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyError, ValueError, OSError) as exc:
        print(f"FROZEN_SECONDARY_ARTIFACT_RECHECK_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
