# Reproduce the paper and atlas

Snapshot: 2026-07-11.

## Environment

- Python 3.10 or newer; runtime scripts use only the standard library.
- `pytest` is optional; the included tests also run with `unittest`.
- `pdflatex` and `bibtex` rebuild the paper.

## Quick package gate

```bash
python scripts/verify_public_package.py
python scripts/recheck_frozen_artifacts.py
python scripts/recheck_catalogue.py
python -m unittest discover -s tests -v
```

This verifies every manifest hash, every public JSON self-hash, the theorem
counts and cross-file joins, the title-named PDF hash, and the private-marker
firewall.

The contact, boundary, cover, and ambient registries are frozen exact secondary
artifacts: this package does not claim to ship their original PAPP production
pipelines.  `recheck_frozen_artifacts.py` verifies their self-hashes, schemas,
statuses, complete parent pins, and exact S5/S6/S7/S8/O1 join.  The O1 headline
gate remains fully replayable from public code.

## Full global-congruence replay

```bash
python scripts/verify_global_congruence.py --print-environment
python scripts/compare_global_replay.py
```

The first command is the expensive exact all-candidate gate.  It writes
`results/global_congruence_gate_replay.json`; the second compares its semantic
invariants and 2,874-row candidate stream with the exported certificate.  Its
wall-clock runtime is machine-dependent because it includes 68,976 exact
corner-locus covariance cases; use the quick package gate for routine edits.

## Build the manuscript

From `paper/`:

```bash
job=The_Nonconvex_A3_Coxeter-Chamber_Atlas
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
bibtex "$job"
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname="$job" main.tex
```

The prebuilt PDF is `paper/The_Nonconvex_A3_Coxeter-Chamber_Atlas.pdf`.  Its hash is separated into
`RELEASE_SHA256.txt` because PDF bytes can vary across TeX distributions; the
environment-independent source and exact data live in `MANIFEST_SHA256.txt`.
