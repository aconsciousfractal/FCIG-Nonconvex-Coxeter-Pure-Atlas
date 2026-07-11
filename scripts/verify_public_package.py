#!/usr/bin/env python3
"""Fast, standard-library verification of the public release candidate."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "connected_nonempty_masks": 1210648,
    "eligible_connected_masks": 67681,
    "canonical_candidates": 2874,
    "all_tilers": 97,
    "convex_tilers": 15,
    "nonconvex_tilers": 82,
    "raw_covers": 786,
    "cover_orbits": 86,
    "raw_multiplier_sets": 1148,
    "multiplier_orbits": 102,
    "ambient_tile_classes": 82,
    "ambient_partition_classes": 86,
}
PRIVATE_13 = "P" + "13"
PRIVATE_17 = "P" + "17"
FORBIDDEN = (
    "paper_projects/" + "13_", "paper_projects\\" + "13_", "SC-P18-" + PRIVATE_13,
    "assigned_" + PRIVATE_13.lower(), "P18-" + PRIVATE_13, "p" + "13_admission",
    "paper_projects/" + "17_", "paper_projects\\" + "17_", "SC-P18-" + PRIVATE_17,
    "assigned_" + PRIVATE_17.lower(), "P18-" + PRIVATE_17, "p" + "17_claim_transfer", "p" + "17_runtime",
    "GitHub" + "_puba", "\\HAN\\" + "FRAMEWORK", "/HAN/" + "FRAMEWORK",
    "18_nonconvex_" + "coxeter_pure_atlas",
)
TEXT_SUFFIXES = {"", ".bib", ".cff", ".csv", ".json", ".md", ".py", ".tex", ".txt", ".yml", ".yaml"}
IGNORED_DIRS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "__pycache__", "results"}
TEX_EPHEMERAL = (".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".run.xml", ".synctex.gz", ".toc")


class VerificationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def ignored(path):
    rel = path.relative_to(ROOT)
    return rel.as_posix() == "paper/main.pdf" or any(part in IGNORED_DIRS for part in rel.parts) or rel.name.lower().endswith(TEX_EPHEMERAL) or rel.name.lower().endswith(".pyc")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest().upper()


def load(name):
    path = ROOT / "artifacts" / name
    value = json.loads(path.read_text(encoding="utf-8"))
    stored = value.pop("payload_sha256_without_self_field")
    require(stored == canonical_sha(value), f"payload self-hash mismatch: {name}")
    value["payload_sha256_without_self_field"] = stored
    return value


def load_self_hashed(rel):
    path = ROOT / rel
    value = json.loads(path.read_text(encoding="utf-8"))
    stored = value.pop("payload_sha256_without_self_field")
    require(stored == canonical_sha(value), f"payload self-hash mismatch: {rel}")
    value["payload_sha256_without_self_field"] = stored
    return value


def check_manifest():
    expected = {}
    for line in (ROOT / "MANIFEST_SHA256.txt").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split(None, 1)
        expected[rel.strip()] = digest.lower()
    for rel, digest in expected.items():
        path = ROOT / rel
        require(path.is_file(), f"manifest file missing: {rel}")
        require(sha(path) == digest, f"manifest mismatch: {rel}")
    actual = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ignored(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in {"MANIFEST_SHA256.txt", "RELEASE_SHA256.txt"}:
            continue
        if rel == "paper/The_Nonconvex_A3_Coxeter-Chamber_Atlas.pdf":
            continue
        actual.add(rel)
    require(set(expected) == actual, "manifest path set differs from repository payload")
    release_line = (ROOT / "RELEASE_SHA256.txt").read_text(encoding="utf-8").strip()
    digest, rel = release_line.split(None, 1)
    require(sha(ROOT / rel.strip()) == digest.lower(), "release PDF hash mismatch")


def check_private_firewall():
    findings = []
    drive_path = re.compile(r"(?i)(?:^|[\"'`\s])[a-z]:[\\/](?=[a-z0-9._-])")
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ignored(path) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN:
            if marker.casefold() in text.casefold():
                findings.append(f"{path.relative_to(ROOT)}:{marker}")
        if drive_path.search(text):
            findings.append(f"{path.relative_to(ROOT)}:absolute-drive-path")
    require(not findings, "private-boundary findings: " + ", ".join(findings[:20]))


def check_latex_artifact_references():
    pattern = re.compile(r"artifacts/[A-Za-z0-9_.-]+[.]json")
    references = set()
    for path in sorted((ROOT / "paper").rglob("*.tex")):
        references.update(pattern.findall(path.read_text(encoding="utf-8")))
    require(references, "paper cites no public JSON artifacts")
    missing = [rel for rel in sorted(references) if not (ROOT / rel).is_file()]
    require(not missing, "paper cites missing public artifacts: " + ", ".join(missing))


def check_provenance(artifact, required_parents, label):
    provenance = artifact.get("provenance", {})
    parents = provenance.get("parents", {})
    require(set(required_parents).issubset(parents), f"missing provenance parent in {label}")
    for parent_name in required_parents:
        pin = parents[parent_name]
        require(pin.get("schema") not in (None, "MISSING_SCHEMA"), f"missing parent schema: {label}/{parent_name}")
        require(pin.get("status") not in (None, "MISSING_STATUS"), f"missing parent status: {label}/{parent_name}")
        require(pin.get("pass") is True, f"nonpassing parent: {label}/{parent_name}")
        require(len(pin.get("source_raw_sha256", "")) == 64, f"bad raw pin: {label}/{parent_name}")
        require(len(pin.get("source_payload_sha256", "")) == 64, f"bad payload pin: {label}/{parent_name}")
        if parent_name == "o1":
            require(len(pin.get("producer_script_sha256", "")) == 64, f"missing O1 producer-script pin: {label}")


def verify_frozen_secondary_artifacts(atlas, contact, boundary, covers, ambient, gate):
    check_provenance(atlas, {"s5", "s6_fingerprint", "s6_contact", "s6_boundary", "s7", "s8", "o1"}, "atlas")
    check_provenance(contact, {"s5", "s6_contact", "o1"}, "contact")
    check_provenance(boundary, {"s5", "s6_boundary", "o1"}, "boundary")
    check_provenance(covers, {"s5", "s7", "o1"}, "covers")
    check_provenance(ambient, {"s5", "s7", "s8", "o1"}, "ambient")
    check_provenance(gate, {"s4", "o1"}, "global gate")
    atlas_ids = {row["row_id"] for row in atlas["rows"]}
    require(len(atlas_ids) == 82, "atlas row IDs are not exactly 82 unique IDs")
    require(atlas_ids == set(contact["panels_by_row_id"]), "contact join differs from atlas")
    require(atlas_ids == {row["row_id"] for row in boundary["rows"]}, "boundary join differs from atlas")
    require(atlas_ids == {row["row_id"] for row in covers["rows"]}, "cover join differs from atlas")
    require(atlas_ids == {row["row_id"] for row in ambient["rows"]}, "ambient join differs from atlas")
    joined_o1_masks = {row["global_congruence_candidate"]["canonical_mask_hex"] for row in atlas["rows"]}
    positive_o1_masks = {row["canonical_mask_hex"] for row in gate["candidate_records"] if row["congruent_exact_cover_exists"] and not row["halfspace_convex"]}
    require(joined_o1_masks == positive_o1_masks, "O1 positive nonconvex join differs from atlas")
    require(atlas["joined_row_stream_sha256"] == canonical_sha(atlas["rows"]), "joined atlas row stream hash mismatch")
    contact_by_id = contact["panels_by_row_id"]
    boundary_by_id = {row["row_id"]: row for row in boundary["rows"]}
    cover_by_id = {row["row_id"]: row for row in covers["rows"]}
    ambient_by_id = {row["row_id"]: row for row in ambient["rows"]}
    o1_by_mask = {row["canonical_mask_hex"]: row for row in gate["candidate_records"] if row["congruent_exact_cover_exists"] and not row["halfspace_convex"]}
    for row in atlas["rows"]:
        pins = row["source_record_pins"]
        require(all(len(value) == 64 for value in pins.values()), f"bad record pin length: {row['row_id']}")
        require(pins["s6_contact_panel_sha256"] == contact_by_id[row["row_id"]]["panel_sha256"], f"contact record pin mismatch: {row['row_id']}")
        require(pins["s6_boundary_record_sha256"] == canonical_sha(boundary_by_id[row["row_id"]]), f"boundary record pin mismatch: {row['row_id']}")
        require(pins["s7_row_record_sha256"] == cover_by_id[row["row_id"]]["row_record_sha256_without_self_field"], f"cover record pin mismatch: {row['row_id']}")
        require(pins["s8_row_record_sha256"] == ambient_by_id[row["row_id"]]["row_record_sha256_without_self_field"], f"ambient record pin mismatch: {row['row_id']}")
        require(pins["o1_candidate_record_sha256"] == canonical_sha(o1_by_mask[row["canonical_mask_hex"]]), f"O1 record pin mismatch: {row['row_id']}")


def main():
    check_manifest()
    bounded = load("bounded_census.json")
    atlas = load("nonconvex_tile_atlas.json")
    contact = load("contact_obstructions.json")
    boundary = load("boundary_presentations.json")
    covers = load("cover_atlas.json")
    ambient = load("ambient_symmetry_atlas.json")
    gate = load("global_congruence_gate.json")
    summary = load("replay_summary.json")
    theorem = load_self_hashed("certificates/THEOREM_REPLAY_CERTIFICATE.json")
    preflight = load_self_hashed("certificates/PACKAGE_PREFLIGHT_CERTIFICATE.json")
    paper_build = load_self_hashed("certificates/PAPER_BUILD_CERTIFICATE.json")
    figure_provenance = load_self_hashed("certificates/FIGURE_PROVENANCE_CERTIFICATE.json")
    source_census = load_self_hashed("data/bounded_census_source.json")
    checks = (
        (summary["counts"] == EXPECTED, "replay summary counts mismatch"),
        (gate["pass"] is True and gate["errors"] == [], "global gate is not passing"),
        (gate["enumeration"]["connected_nonempty_masks"] == EXPECTED["connected_nonempty_masks"], "connected-mask count mismatch"),
        (gate["enumeration"]["eligible_connected_masks"] == EXPECTED["eligible_connected_masks"], "eligible-mask count mismatch"),
        (gate["enumeration"]["canonical_left_orbit_candidates"] == EXPECTED["canonical_candidates"], "canonical candidate count mismatch"),
        (len(gate["candidate_records"]) == EXPECTED["canonical_candidates"], "candidate record length mismatch"),
        (gate["global_congruence_gate"]["graph_gram_disagreement_count"] == 0, "isometry lanes disagree"),
        (gate["global_congruence_gate"]["non_S4_corner_isometry_map_count"] == 0, "non-S4 corner map found"),
        (gate["global_congruence_gate"]["rank3_nonvertex_edge_stratum_candidate_count"] == 0, "rank-three nonvertex edge stratum found"),
        (gate["congruent_copy_exact_cover"]["positive_classes"] == EXPECTED["all_tilers"], "tiler count mismatch"),
        (gate["congruent_copy_exact_cover"]["convex_positive_classes"] == EXPECTED["convex_tilers"], "convex tiler count mismatch"),
        (gate["congruent_copy_exact_cover"]["nonconvex_positive_classes"] == EXPECTED["nonconvex_tilers"], "nonconvex tiler count mismatch"),
        (len(atlas["rows"]) == EXPECTED["nonconvex_tilers"], "atlas length mismatch"),
        (len(covers["rows"]) == EXPECTED["nonconvex_tilers"], "cover row length mismatch"),
        (len(ambient["rows"]) == EXPECTED["ambient_tile_classes"], "ambient row length mismatch"),
        (len(ambient["ambient_partition_congruence_classes"]) == EXPECTED["ambient_partition_classes"], "ambient partition count mismatch"),
        (covers["summary"]["raw_unordered_exact_cover_count"] == EXPECTED["raw_covers"], "raw cover count mismatch"),
        (covers["summary"]["global_left_cover_orbit_count"] == EXPECTED["cover_orbits"], "cover orbit count mismatch"),
        (covers["summary"]["raw_multiplier_set_count"] == EXPECTED["raw_multiplier_sets"], "raw multiplier count mismatch"),
        (covers["summary"]["global_left_multiplier_orbit_count"] == EXPECTED["multiplier_orbits"], "multiplier orbit count mismatch"),
        (contact["summary"]["selected_cover_count"] == 82, "contact panel count mismatch"),
        (boundary["summary"]["row_count"] == 82, "boundary row count mismatch"),
        (bounded["tiler_search"]["total_tiler_orbits"] == EXPECTED["all_tilers"], "public bounded census mismatch"),
        (source_census["tiler_search"]["total_tiler_orbits"] == EXPECTED["all_tilers"], "source bounded census mismatch"),
        (paper_build["pass"] is True, "fresh staged paper certificate is not passing"),
        (paper_build["pdf_sha256"].lower() == sha(ROOT / paper_build["pdf_path"]), "paper build certificate PDF hash mismatch"),
        (figure_provenance["pass"] is True, "figure provenance certificate is not passing"),
    )
    for condition, message in checks:
        require(condition, message)
    for rel, expected_rows in (
        ("tables/nonconvex_atlas.csv", 82),
        ("tables/all_eligible_candidates.csv", EXPECTED["canonical_candidates"]),
    ):
        csv_bytes = (ROOT / rel).read_bytes()
        require(b"\r\n" not in csv_bytes, f"CSV is not LF-only: {rel}")
        parsed = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"), newline="")))
        require(len(parsed) == expected_rows, f"CSV row count mismatch: {rel}")
    candidate_fields = set(parsed[0])
    require("corner_s4_class_id" in candidate_fields, "candidate CSV lacks corner_s4_class_id")
    require("c3_covariance_globally_certified" in candidate_fields, "candidate CSV lacks C3 covariance field")
    for figure in figure_provenance["figures"]:
        require(figure["sha256"].lower() == sha(ROOT / figure["exported_path"]), f"figure provenance hash mismatch: {figure['exported_path']}")
        require((ROOT / figure["exported_path"]).stat().st_size == figure["bytes"], f"figure provenance size mismatch: {figure['exported_path']}")
    verify_frozen_secondary_artifacts(atlas, contact, boundary, covers, ambient, gate)
    artifact_hashes = {
        "ambient_symmetry_atlas.json": ambient["payload_sha256_without_self_field"],
        "boundary_presentations.json": boundary["payload_sha256_without_self_field"],
        "bounded_census.json": bounded["payload_sha256_without_self_field"],
        "contact_obstructions.json": contact["payload_sha256_without_self_field"],
        "cover_atlas.json": covers["payload_sha256_without_self_field"],
        "global_congruence_gate.json": gate["payload_sha256_without_self_field"],
        "nonconvex_tile_atlas.json": atlas["payload_sha256_without_self_field"],
        "replay_summary.json": summary["payload_sha256_without_self_field"],
    }
    require(theorem["artifact_payload_sha256"] == artifact_hashes, "theorem artifact hash map mismatch")
    require(theorem["publication_authorized"] is False, "theorem certificate authorizes publication")
    require(preflight["publication_authorized"] is False, "preflight certificate authorizes publication")
    check_latex_artifact_references()
    check_private_firewall()
    print("PUBLIC_QUICK_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VerificationError, KeyError, ValueError, OSError) as exc:
        print(f"PUBLIC_QUICK_VERIFY_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
