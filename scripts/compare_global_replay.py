#!/usr/bin/env python3
"""Compare a fresh full replay with the exported semantic certificate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "artifacts" / "global_congruence_gate.json"
REPLAY = ROOT / "results" / "global_congruence_gate_replay.json"


class ReplayMismatch(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ReplayMismatch(message)


def main():
    if not REPLAY.is_file():
        print("missing replay; run scripts/verify_global_congruence.py first", file=sys.stderr)
        return 1
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    require(replay["pass"] is True and replay["errors"] == [], "fresh replay is not passing")
    pairs = (
        (cert["enumeration"], replay["enumeration"], "enumeration"),
        (cert["global_congruence_gate"], replay["global_congruence_gate"], "global_congruence_gate"),
        (cert["congruent_copy_exact_cover"], replay["congruent_copy_exact_cover"], "congruent_copy_exact_cover"),
        (cert["candidate_records"], replay["candidate_records"], "candidate_records"),
        (cert["candidate_record_stream_sha256"], replay["candidate_record_stream_sha256"], "candidate stream hash"),
    )
    for expected, actual, label in pairs:
        require(expected == actual, f"semantic mismatch: {label}")
    print("GLOBAL_CONGRUENCE_REPLAY_SEMANTIC_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReplayMismatch, KeyError, ValueError, OSError) as exc:
        print(f"GLOBAL_CONGRUENCE_REPLAY_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
