#!/usr/bin/env python3
# Public standalone replay generated from the exact internal gate.
# Code license: MIT.  The semantic comparison target is in artifacts/.
"""Close the P18/T2-O1 congruence-versus-left-orbit finite gap.

The S4 census decides exact covers made from left translates.  T2's open
problem, however, asks for covers by freely Euclidean-congruent Coxeter-pure
pieces.  This gate exhausts every left-orbit representative of every
facet-connected chamber union whose size divides 24, and proves on that
finite carrier that free congruence creates no extra identifications.

The proof screen is deliberately fail-closed.  It imports the exact S8
geometry primitives, reconstructs the rank-three boundary-plane corner locus
for all candidates, and independently enumerates every exact corner-set
isometry by both the distance-graph and affine/Gram lanes.  The gate passes
only if every locus spans, no rank-three nonvertex boundary stratum is missed,
and every enumerated map is one of the 24 coordinate permutations.  It then
reruns exact cover using the now-complete congruence class of each candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


ROOT = Path(__file__).resolve().parents[1]
S8_SCRIPT = ROOT / "scripts" / "geometry_core.py"
S4_RESULT = ROOT / "data" / "bounded_census_source.json"
DEFAULT_OUT = ROOT / "results" / "global_congruence_gate_replay.json"

SCHEMA = "fcig.nonconvex_a3.public.global_congruence_replay.v1"
DATE = "2026-07-11"
DIVISOR_SIZES = frozenset((1, 2, 3, 4, 6, 8, 12, 24))


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s8 = load_module(S8_SCRIPT, "public_a3_geometry_for_global_gate")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def render_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def payload_self_hash_ok(value: dict[str, Any]) -> bool:
    clean = dict(value)
    stored = clean.pop("payload_sha256_without_self_field", None)
    return stored == canonical_sha256(clean)


def histogram(counter: Counter[int] | Counter[str]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter)}


def fraction_pair(value: Any) -> list[int]:
    return [value.numerator, value.denominator]


def serialize_distance_signature(signature: Sequence[Any]) -> list[list[int]]:
    return [fraction_pair(value) for value in signature]


def build_adjacency_masks() -> tuple[int, ...]:
    rows: list[int] = []
    for chamber in range(24):
        rows.append(
            sum(
                1 << s8.RIGHT_MAPS[generator][chamber]
                for generator in s8.SIMPLE_RIGHT_GENERATORS
            )
        )
    return tuple(rows)


ADJ_MASK = build_adjacency_masks()


def enumerate_connected() -> Iterator[int]:
    """Simple connected-subgraph enumeration; every nonempty mask once."""
    for root in range(24):
        yield from extend_connected(1 << root, (1 << root) - 1)


def extend_connected(mask: int, forbidden: int) -> Iterator[int]:
    yield mask
    neighbors = 0
    work = mask
    while work:
        bit = work & -work
        neighbors |= ADJ_MASK[bit.bit_length() - 1]
        work ^= bit
    available = neighbors & s8.ALL_CHAMBERS & ~mask & ~forbidden
    while available:
        bit = available & -available
        yield from extend_connected(mask | bit, forbidden)
        forbidden |= bit
        available ^= bit


def canonical_left(mask: int) -> int:
    return min(s8.apply_left_mask(g, mask) for g in range(24))


def left_orbit(mask: int) -> tuple[int, ...]:
    return tuple(sorted({s8.apply_left_mask(g, mask) for g in range(24)}))


def build_pair_halfspaces() -> tuple[int, ...]:
    rows: list[int] = []
    for i, j in itertools.combinations(range(4), 2):
        row = 0
        for chamber, word in enumerate(s8.G):
            if word.index(i) < word.index(j):
                row |= 1 << chamber
        rows.append(row)
    return tuple(rows)


PAIR_PLUS = build_pair_halfspaces()


def halfspace_closure(mask: int) -> int:
    allowed = s8.ALL_CHAMBERS
    for plus in PAIR_PLUS:
        if mask & plus == mask:
            allowed &= plus
        elif mask & (s8.ALL_CHAMBERS ^ plus) == mask:
            allowed &= s8.ALL_CHAMBERS ^ plus
    return allowed


def exact_cover_witness(mask: int) -> tuple[int, ...] | None:
    """Exact cover over all chamber-union copies in the left orbit."""
    k = mask.bit_count()
    if not mask or 24 % k:
        return None
    rows = left_orbit(mask)
    by_column = tuple(
        tuple(row for row in rows if row & (1 << column))
        for column in range(24)
    )
    target_pieces = 24 // k
    failed: set[int] = set()

    def search(remaining: int, chosen: tuple[int, ...]) -> tuple[int, ...] | None:
        if remaining == 0:
            return chosen
        if remaining in failed or len(chosen) >= target_pieces:
            return None
        choices: tuple[int, ...] | None = None
        work = remaining
        while work:
            bit = work & -work
            column = bit.bit_length() - 1
            candidates = tuple(
                row for row in by_column[column] if row & remaining == row
            )
            if not candidates:
                failed.add(remaining)
                return None
            if choices is None or len(candidates) < len(choices):
                choices = candidates
                if len(choices) == 1:
                    break
            work ^= bit
        if choices is None:
            raise RuntimeError("exact-cover branch has no choices")
        for row in choices:
            answer = search(remaining ^ row, chosen + (row,))
            if answer is not None:
                return answer
        failed.add(remaining)
        return None

    return search(s8.ALL_CHAMBERS, ())


def enumerate_candidates() -> tuple[list[int], dict[str, Any]]:
    connected_total = 0
    eligible_total = 0
    connected_by_size: Counter[int] = Counter()
    eligible_by_size: Counter[int] = Counter()
    canonical_masks: set[int] = set()
    connected_stream = hashlib.sha256()
    for mask in enumerate_connected():
        connected_total += 1
        k = mask.bit_count()
        connected_by_size[k] += 1
        connected_stream.update(mask.to_bytes(3, "little"))
        if k not in DIVISOR_SIZES:
            continue
        eligible_total += 1
        eligible_by_size[k] += 1
        canonical_masks.add(canonical_left(mask))
    candidates = sorted(canonical_masks, key=lambda mask: (mask.bit_count(), mask))
    canonical_by_size = Counter(mask.bit_count() for mask in candidates)
    return candidates, {
        "connected_nonempty_masks": connected_total,
        "connected_by_size": histogram(connected_by_size),
        "connected_scs_order_mask_stream_sha256": connected_stream.hexdigest().upper(),
        "eligible_connected_masks": eligible_total,
        "eligible_by_size": histogram(eligible_by_size),
        "canonical_left_orbit_candidates": len(candidates),
        "canonical_candidates_by_size": histogram(canonical_by_size),
        "canonical_candidate_mask_stream_sha256": canonical_sha256(
            [f"{mask:06X}" for mask in candidates]
        ),
    }


def geometry_record(mask: int) -> dict[str, Any]:
    boundary = s8.boundary_corner_locus(mask)
    corners = boundary["corners"]
    matrix = s8.distance_matrix(corners)
    distance_signature = s8.global_distance_signature(matrix)
    edge_normal_lines: dict[tuple[Any, Any], set[tuple[int, int, int, int]]] = (
        defaultdict(set)
    )
    for triangle in boundary["boundary_triangles_exact"]:
        p0, p1, p2 = triangle
        normal = s8.primitive_integer_vector(
            s8.null_normal(s8.sub(p1, p0), s8.sub(p2, p0))
        )
        for edge in itertools.combinations(triangle, 2):
            edge_normal_lines[tuple(sorted(edge))].add(normal)
    rank3_edge_strata = tuple(
        edge
        for edge, normals in edge_normal_lines.items()
        if s8.rational_rank(normals) >= 3
    )
    corner_images = tuple(
        (tuple(sorted(s8.phi_point(g, point) for point in corners)), g)
        for g in range(24)
    )
    canonical_corners, corner_transporter = min(corner_images)
    return {
        "mask": mask,
        "k": mask.bit_count(),
        "boundary": boundary,
        "corners": corners,
        "matrix": matrix,
        "bucket": (mask.bit_count(), len(corners), distance_signature),
        "rank3_nonvertex_edge_stratum_count": len(rank3_edge_strata),
        "canonical_corners": canonical_corners,
        "corner_class_key": (mask.bit_count(), canonical_corners),
        "corner_class_transporter_g": corner_transporter,
        "corner_coordinate_sha256": canonical_sha256(
            [[fraction_pair(value) for value in point] for point in corners]
        ),
        "distance_signature_sha256": canonical_sha256(
            serialize_distance_signature(distance_signature)
        ),
    }


def unordered_pair_count(n: int) -> int:
    return n * (n + 1) // 2


def global_corner_covariance_audit() -> dict[str, Any]:
    """Prove C3(Phi_g U)=Phi_g C3(U) for every chamber mask U.

    The proof is mask-independent.  We exhaust the finite chamber/facet
    primitives and record the deduction from their exact equivariance.
    """
    errors: list[str] = []
    chamber_bijection_cases = 0
    chamber_tetrahedron_cases = 0
    mesh_vertex_cases = 0
    facet_occurrence_cases = 0
    facet_incidence_equivalence_cases = 0
    normal_line_cases = 0
    occurrences = tuple(
        (chamber, omitted)
        for chamber in range(24)
        for omitted in range(4)
    )
    for g in range(24):
        chamber_bijection_cases += 1
        if len(set(s8.LEFT_MAPS[g])) != 24:
            errors.append(f"left chamber map is not bijective for {s8.WORDS[g]}")
        for point in s8.ALL_BARYCENTRIC_VERTICES:
            mesh_vertex_cases += 1
            if s8.phi_point(g, point) not in s8.ALL_BARYCENTRIC_VERTICES:
                errors.append(f"mesh vertex leaves carrier for {s8.WORDS[g]}")
        source_facet_keys: list[tuple[Any, ...]] = []
        target_facet_keys: list[tuple[Any, ...]] = []
        for chamber in range(24):
            moved_chamber = s8.LEFT_MAPS[g][chamber]
            chamber_tetrahedron_cases += 1
            moved_tetrahedron = tuple(
                s8.phi_point(g, point)
                for point in s8.CHAMBER_VERTICES[chamber]
            )
            if moved_tetrahedron != s8.CHAMBER_VERTICES[moved_chamber]:
                errors.append(
                    f"chamber tetrahedron covariance failed: {s8.WORDS[g]} on {s8.WORDS[chamber]}"
                )
            for omitted in range(4):
                facet_occurrence_cases += 1
                source_triangle = tuple(
                    sorted(
                        s8.CHAMBER_VERTICES[chamber][j]
                        for j in range(4)
                        if j != omitted
                    )
                )
                target_triangle = tuple(
                    sorted(
                        s8.CHAMBER_VERTICES[moved_chamber][j]
                        for j in range(4)
                        if j != omitted
                    )
                )
                moved_triangle = tuple(
                    sorted(s8.phi_point(g, point) for point in source_triangle)
                )
                source_facet_keys.append(source_triangle)
                target_facet_keys.append(target_triangle)
                if moved_triangle != target_triangle:
                    errors.append(
                        f"facet occurrence covariance failed: {s8.WORDS[g]}/{s8.WORDS[chamber]}/{omitted}"
                    )
                sp0, sp1, sp2 = source_triangle
                tp0, tp1, tp2 = target_triangle
                source_normal = s8.null_normal(
                    s8.sub(sp1, sp0), s8.sub(sp2, sp0)
                )
                target_normal = s8.null_normal(
                    s8.sub(tp1, tp0), s8.sub(tp2, tp0)
                )
                moved_normal_line = s8.primitive_integer_vector(
                    s8.phi_point(g, source_normal)
                )
                target_normal_line = s8.primitive_integer_vector(target_normal)
                normal_line_cases += 1
                if moved_normal_line != target_normal_line:
                    errors.append(
                        f"facet normal-line covariance failed: {s8.WORDS[g]}/{s8.WORDS[chamber]}/{omitted}"
                    )
        for a, b in itertools.combinations(range(len(occurrences)), 2):
            facet_incidence_equivalence_cases += 1
            if (source_facet_keys[a] == source_facet_keys[b]) != (
                target_facet_keys[a] == target_facet_keys[b]
            ):
                errors.append(
                    f"facet incidence equivalence failed: {s8.WORDS[g]}/{a}/{b}"
                )
    return {
        "pass": not errors,
        "errors": errors,
        "left_chamber_bijection_cases": chamber_bijection_cases,
        "chamber_tetrahedron_covariance_cases": chamber_tetrahedron_cases,
        "barycentric_mesh_vertex_covariance_cases": mesh_vertex_cases,
        "chamber_facet_occurrence_covariance_cases": facet_occurrence_cases,
        "facet_occurrence_incidence_equivalence_cases": (
            facet_incidence_equivalence_cases
        ),
        "primitive_boundary_plane_normal_line_covariance_cases": normal_line_cases,
        "candidate_C3_covariance_cases_implied": 2874 * 24,
        "deduction": [
            "Phi_g bijects the 24 chambers and the 96 chamber-facet occurrences.",
            "Facet-key equality is preserved, hence every selected-mask boundary-facet incidence multiplicity is preserved.",
            "Every boundary triangle and its primitive normal line transform exactly under Phi_g.",
            "Coordinate permutation is an invertible orthogonal linear map, so it preserves the rank of every local set of plane-normal lines.",
            "Therefore boundary extraction, local boundary-plane germs, normal-span rank, and C3 commute with Phi_g for every one of the 2^24 chamber masks.",
        ],
    }


def classify_congruence(
    geometry: list[dict[str, Any]], errors: list[str]
) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    by_k: dict[int, list[dict[str, Any]]] = defaultdict(list)
    original_buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    corner_classes: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    corner_count_hist: Counter[int] = Counter()
    affine_rank_hist: Counter[int] = Counter()
    manifold_failure_rows: list[str] = []
    invalid_facet_rows: list[str] = []
    rank3_edge_stratum_rows: list[str] = []
    covariance_audit = global_corner_covariance_audit()
    errors.extend(
        f"global C3 covariance: {error}" for error in covariance_audit["errors"]
    )
    for record in geometry:
        by_k[record["k"]].append(record)
        original_buckets[record["bucket"]].append(record)
        corner_classes[record["corner_class_key"]].append(record)
        boundary = record["boundary"]
        corner_count_hist[len(record["corners"])] += 1
        affine_rank_hist[boundary["affine_rank"]] += 1
        if boundary["invalid_facet_incidence"]:
            invalid_facet_rows.append(f"{record['mask']:06X}")
        if boundary["manifold_edge_failures"]:
            manifold_failure_rows.append(f"{record['mask']:06X}")
        if record["rank3_nonvertex_edge_stratum_count"]:
            rank3_edge_stratum_rows.append(f"{record['mask']:06X}")
        if boundary["affine_rank"] != 3:
            errors.append(
                f"rank-three corner locus does not span H for {record['mask']:06X}"
            )
    if invalid_facet_rows:
        errors.append(
            f"invalid boundary-facet incidence on {len(invalid_facet_rows)} candidates"
        )
    if rank3_edge_stratum_rows:
        errors.append(
            "rank-three nonvertex boundary edge strata on "
            f"{len(rank3_edge_stratum_rows)} candidates"
        )

    total_pairs = unordered_pair_count(len(geometry))
    within_k_pairs = sum(unordered_pair_count(len(rows)) for rows in by_k.values())
    original_signature_pairs = sum(
        unordered_pair_count(len(rows)) for rows in original_buckets.values()
    )
    volume_rejected_pairs = total_pairs - within_k_pairs
    distance_rejected_pairs = within_k_pairs - original_signature_pairs

    # Exact S4 covariance reduces 2,874 corner loci to canonical corner-set
    # classes.  Isometries inside one class are generated from one diagonal
    # automorphism list by conjugating with the recorded S4 transporters.
    class_records: list[dict[str, Any]] = []
    class_members: dict[str, list[dict[str, Any]]] = {}
    for (k, canonical_corners), members in corner_classes.items():
        serial = [[fraction_pair(value) for value in point] for point in canonical_corners]
        class_id = f"P18-S13-O1-C3-K{k:02d}-{canonical_sha256(serial)}"
        matrix = s8.distance_matrix(canonical_corners)
        class_record = {
            "class_id": class_id,
            "k": k,
            "corners": canonical_corners,
            "matrix": matrix,
            "signature": (k, len(canonical_corners), s8.global_distance_signature(matrix)),
        }
        class_records.append(class_record)
        class_members[class_id] = members
        for member in members:
            member["corner_class_id"] = class_id
    class_records.sort(key=lambda record: record["class_id"])
    class_buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in class_records:
        class_buckets[record["signature"]].append(record)
    class_pairs_evaluated = sum(
        unordered_pair_count(len(rows)) for rows in class_buckets.values()
    )

    map_stream = hashlib.sha256()
    graph_gram_disagreements = 0
    exact_class_maps = 0
    non_s4_maps = 0
    cross_class_corner_isometric_pairs = 0
    orientation_counts: Counter[str] = Counter()
    class_self_map_count: dict[str, int] = {}
    non_s4_examples: list[dict[str, Any]] = []

    for bucket_key in sorted(class_buckets, key=lambda key: canonical_sha256(str(key))):
        rows = sorted(class_buckets[bucket_key], key=lambda record: record["class_id"])
        for source_index, source in enumerate(rows):
            for target in rows[source_index:]:
                graph_maps = s8.distance_graph_isomorphisms(
                    source["matrix"], target["matrix"]
                )
                gram_maps = s8.affine_gram_isomorphisms(
                    source["corners"],
                    target["corners"],
                    source["matrix"],
                    target["matrix"],
                )
                if graph_maps != gram_maps:
                    graph_gram_disagreements += 1
                    errors.append(
                        "Gram/graph disagreement for "
                        f"{source['class_id']}->{target['class_id']}"
                    )
                if not graph_maps:
                    continue
                diagonal = source["class_id"] == target["class_id"]
                if not diagonal:
                    cross_class_corner_isometric_pairs += 1
                else:
                    class_self_map_count[source["class_id"]] = len(graph_maps)
                for mapping in graph_maps:
                    exact_class_maps += 1
                    g = s8.coordinate_permutation_for_mapping(
                        source["corners"], target["corners"], mapping
                    )
                    sign = s8.orientation_sign(
                        source["corners"], target["corners"], mapping
                    )
                    orientation_counts[
                        "preserving" if sign == 1 else "reversing"
                    ] += 1
                    packet = [
                        source["class_id"],
                        target["class_id"],
                        list(mapping),
                        s8.WORDS[g] if g is not None else None,
                        sign,
                    ]
                    map_stream.update(canonical_json_bytes(packet) + b"\n")
                    if g is None:
                        non_s4_maps += 1
                        if len(non_s4_examples) < 20:
                            non_s4_examples.append(
                                {
                                    "source_corner_class_id": source["class_id"],
                                    "target_corner_class_id": target["class_id"],
                                    "source_to_target_corner_indices": list(mapping),
                                    "orientation_on_H": sign,
                                }
                            )
                        continue
    if non_s4_maps:
        errors.append(f"found {non_s4_maps} non-S4 corner-set isometry maps")
    if cross_class_corner_isometric_pairs:
        errors.append(
            "distinct canonical S4 corner classes are isometric on "
            f"{cross_class_corner_isometric_pairs} pairs"
        )

    missing_diagonal_classes = sorted(
        set(class_members) - set(class_self_map_count)
    )
    if missing_diagonal_classes:
        errors.append(
            f"missing diagonal corner isometries for {len(missing_diagonal_classes)} classes"
        )

    per_mask: dict[int, dict[str, Any]] = {}
    derived_cross_candidate_pairs = 0
    derived_original_pair_maps = 0
    actual_shape_self_maps = 0
    for class_id, members in class_members.items():
        self_maps = class_self_map_count.get(class_id, 0)
        member_count = len(members)
        derived_cross_candidate_pairs += member_count * (member_count - 1) // 2
        derived_original_pair_maps += self_maps * unordered_pair_count(member_count)
        for member in members:
            shape_self = sum(
                s8.apply_left_mask(g, member["mask"]) == member["mask"]
                for g in range(24)
            )
            actual_shape_self_maps += shape_self
            per_mask[member["mask"]] = {
                "corner_S4_class_id": class_id,
                "corner_class_transporter_word_zero_based": s8.WORDS[
                    member["corner_class_transporter_g"]
                ],
                "corner_self_isometry_count": self_maps,
                "actual_shape_self_isometry_count": shape_self,
                "cross_candidate_corner_isometry_pair_count": member_count - 1,
            }

    largest_bucket = max((len(rows) for rows in original_buckets.values()), default=0)
    largest_class_bucket = max((len(rows) for rows in class_buckets.values()), default=0)
    return {
        "proof_dictionary": [
            "congruent chamber unions have equal volume, hence equal chamber count k",
            "a Euclidean shape isometry maps the intrinsic rank-three boundary-plane corner locus isometrically",
            "face interiors have normal rank one; the exact edge-stratum audit has rank at most two, so every rank-three point is a mesh vertex",
            "affine-rank three makes a corner-set isometry determine the ambient isometry uniquely",
            "exact S4 covariance reduces all candidate loci to canonical S4 corner classes without losing any isometry",
            "exact distance-graph and affine/Gram lanes independently enumerate every corner-set isometry",
            "every enumerated map is a coordinate permutation Phi_g, so any congruent chamber union is a left translate",
        ],
        "candidate_count": len(geometry),
        "corner_count_histogram": histogram(corner_count_hist),
        "corner_affine_rank_histogram": histogram(affine_rank_hist),
        "all_corner_loci_affinely_span_H": all(
            record["boundary"]["affine_rank"] == 3 for record in geometry
        ),
        "invalid_facet_incidence_candidate_count": len(invalid_facet_rows),
        "invalid_facet_incidence_first_masks_hex": invalid_facet_rows[:20],
        "nonmanifold_boundary_candidate_count": len(manifold_failure_rows),
        "nonmanifold_boundary_first_masks_hex": manifold_failure_rows[:20],
        "rank3_nonvertex_edge_stratum_candidate_count": len(rank3_edge_stratum_rows),
        "rank3_nonvertex_edge_stratum_first_masks_hex": rank3_edge_stratum_rows[:20],
        "global_C3_covariance_audit": covariance_audit,
        "distance_signature_bucket_count": len(original_buckets),
        "largest_distance_signature_bucket": largest_bucket,
        "all_unordered_pairs_including_diagonal": total_pairs,
        "volume_rejected_pairs": volume_rejected_pairs,
        "corner_distance_signature_rejected_pairs_with_equal_volume": distance_rejected_pairs,
        "original_pairs_surviving_volume_and_distance_invariants": original_signature_pairs,
        "pair_accounting_identity_holds": (
            volume_rejected_pairs + distance_rejected_pairs + original_signature_pairs
            == total_pairs
        ),
        "canonical_S4_corner_class_count": len(class_records),
        "canonical_corner_class_distance_signature_bucket_count": len(class_buckets),
        "largest_canonical_corner_class_signature_bucket": largest_class_bucket,
        "canonical_corner_class_pairs_exhausted_by_both_exact_lanes": class_pairs_evaluated,
        "cross_canonical_corner_class_isometric_pairs": cross_class_corner_isometric_pairs,
        "exact_corner_isometry_maps_on_canonical_classes": exact_class_maps,
        "derived_cross_candidate_corner_isometric_pairs": derived_cross_candidate_pairs,
        "derived_corner_isometry_maps_on_all_candidate_pairs": derived_original_pair_maps,
        "actual_shape_self_isometry_maps_over_all_candidates": actual_shape_self_maps,
        "orientation_of_exact_class_corner_maps": dict(sorted(orientation_counts.items())),
        "graph_gram_disagreement_count": graph_gram_disagreements,
        "non_S4_corner_isometry_map_count": non_s4_maps,
        "non_S4_first_examples": non_s4_examples,
        "corner_isometry_map_stream_sha256": map_stream.hexdigest().upper(),
        "conclusion_if_pass": (
            "free Euclidean congruence between eligible connected chamber unions "
            "equals locked left-S4 orbit equivalence"
        ),
    }, per_mask


def run_exact_cover(
    candidates: Sequence[int], s4_result: dict[str, Any], errors: list[str]
) -> tuple[dict[str, Any], dict[int, tuple[int, ...] | None]]:
    witnesses: dict[int, tuple[int, ...] | None] = {}
    positive: list[int] = []
    convex_positive: list[int] = []
    nonconvex_positive: list[int] = []
    by_k_positive: Counter[int] = Counter()
    for mask in candidates:
        witness = exact_cover_witness(mask)
        witnesses[mask] = witness
        if witness is None:
            continue
        positive.append(mask)
        by_k_positive[mask.bit_count()] += 1
        if halfspace_closure(mask) == mask:
            convex_positive.append(mask)
        else:
            nonconvex_positive.append(mask)

    expected_records = s4_result.get("tiler_search", {}).get("records", [])
    expected = sorted(int(record["mask_hex"], 16) for record in expected_records)
    if sorted(positive) != expected:
        missing = sorted(set(expected) - set(positive))
        extra = sorted(set(positive) - set(expected))
        errors.append(
            "S13-O1 exact-cover set disagrees with S4: "
            f"missing={[f'{mask:06X}' for mask in missing[:20]]}, "
            f"extra={[f'{mask:06X}' for mask in extra[:20]]}"
        )
    return {
        "search_semantics": (
            "after the global rigidity gate, the complete set of eligible "
            "chamber-union copies congruent to U is exactly {g.U:g in S4}"
        ),
        "canonical_congruence_classes_decided": len(candidates),
        "negative_classes": len(candidates) - len(positive),
        "positive_classes": len(positive),
        "convex_positive_classes": len(convex_positive),
        "nonconvex_positive_classes": len(nonconvex_positive),
        "positive_by_k": histogram(by_k_positive),
        "positive_mask_stream_sha256": canonical_sha256(
            [f"{mask:06X}" for mask in sorted(positive)]
        ),
        "positive_set_equals_S4_certified_set": sorted(positive) == expected,
        "nonconvex_positive_masks_hex": [
            f"{mask:06X}" for mask in nonconvex_positive
        ],
        "conclusion_if_pass": (
            "exactly 97 connected Coxeter-pure congruence classes tile T: "
            "15 convex and 82 nonconvex"
        ),
    }, witnesses


def validate_pinned_s4(s4_result: dict[str, Any], errors: list[str]) -> None:
    if s4_result.get("schema") != "fcig.p18.s4.independent_bounded_census.v1":
        errors.append("unexpected P18-S4 result schema")
    if not payload_self_hash_ok(s4_result):
        errors.append("P18-S4 result payload self-hash mismatch")
    expected = s4_result.get("tiler_search", {})
    if (
        expected.get("eligible_connected_masks"),
        expected.get("canonical_eligible_tile_orbits"),
        expected.get("total_tiler_orbits"),
    ) != (67681, 2874, 97):
        errors.append("P18-S4 locked census totals are not 67681/2874/97")


def build_result() -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    s4_result = json.loads(S4_RESULT.read_text(encoding="utf-8"))
    validate_pinned_s4(s4_result, errors)

    candidates, enumeration = enumerate_candidates()
    locked = s4_result.get("tiler_search", {})
    if enumeration["connected_nonempty_masks"] != 1210648:
        errors.append("connected census is not 1,210,648")
    if enumeration["eligible_connected_masks"] != locked.get(
        "eligible_connected_masks"
    ):
        errors.append("eligible connected mask count disagrees with S4")
    if enumeration["canonical_left_orbit_candidates"] != locked.get(
        "canonical_eligible_tile_orbits"
    ):
        errors.append("canonical candidate count disagrees with S4")

    geometry = [geometry_record(mask) for mask in candidates]
    congruence, per_mask = classify_congruence(geometry, errors)
    exact_cover, witnesses = run_exact_cover(candidates, s4_result, errors)

    candidate_records: list[dict[str, Any]] = []
    for record in geometry:
        mask = record["mask"]
        witness = witnesses[mask]
        candidate_records.append(
            {
                "candidate_id": f"P18-S13-O1-K{record['k']:02d}-M{mask:06X}",
                "canonical_mask_hex": f"{mask:06X}",
                "k": record["k"],
                "left_orbit_size": len(left_orbit(mask)),
                "rank3_corner_count": len(record["corners"]),
                "rank3_corner_affine_rank": record["boundary"]["affine_rank"],
                "boundary_manifold_edge_failures": record["boundary"][
                    "manifold_edge_failures"
                ],
                "rank3_nonvertex_edge_stratum_count": record[
                    "rank3_nonvertex_edge_stratum_count"
                ],
                "corner_S4_covariance_covered_by_global_primitive_proof": True,
                "corner_coordinate_sha256": record["corner_coordinate_sha256"],
                "corner_distance_signature_sha256": record[
                    "distance_signature_sha256"
                ],
                **per_mask[mask],
                "congruent_exact_cover_exists": witness is not None,
                "exact_cover_witness_masks_hex": (
                    [f"{piece:06X}" for piece in witness]
                    if witness is not None
                    else []
                ),
                "halfspace_convex": halfspace_closure(mask) == mask,
            }
        )

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "project": "FCIG-Nonconvex-Coxeter-Pure-Atlas",
        "gate": "GLOBAL-CONGRUENCE-REPLAY",
        "date": DATE,
        "status": (
            "PASS_GLOBAL_CONGRUENCE_EQUALS_LEFT_S4_AND_EXACT_COVER_COMPLETE"
            if not errors
            else "STOP_FAIL_CLOSED"
        ),
        "pass": not errors,
        "scope": {
            "carrier": (
                "nonempty facet-connected unions of the fixed 24 closed A3 "
                "Coxeter chambers in the regular tetrahedron"
            ),
            "candidate_filter": "chamber count k divides 24",
            "copy_relation": "arbitrary Euclidean congruence between chamber-union polyhedral sets",
            "cover_relation": "pairwise interior-disjoint chamber masks with union all 24 chambers",
            "nonclaims": [
                "arbitrary tetrahedron dissections not aligned to the A3 chamber carrier",
                "disconnected chamber unions",
                "structural classification beyond this exact finite carrier",
                "formal proof or independent red-team approval",
            ],
        },
        "input_pins": {
            "bounded_census_relative_path": str(S4_RESULT.relative_to(ROOT)).replace("\\", "/"),
            "bounded_census_raw_sha256": sha256_file(S4_RESULT),
            "bounded_census_payload_sha256": s4_result.get(
                "payload_sha256_without_self_field"
            ),
            "geometry_core_relative_path": str(S8_SCRIPT.relative_to(ROOT)).replace("\\", "/"),
            "geometry_core_raw_sha256": sha256_file(S8_SCRIPT),
        },
        "enumeration": enumeration,
        "global_congruence_gate": congruence,
        "congruent_copy_exact_cover": exact_cover,
        "candidate_records": candidate_records,
        "candidate_record_stream_sha256": canonical_sha256(candidate_records),
        "errors": errors,
        "deterministic_result_excludes_runtime": True,
    }
    result["payload_sha256_without_self_field"] = canonical_sha256(result)
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidates": len(candidates),
                "canonical_corner_classes": congruence[
                    "canonical_S4_corner_class_count"
                ],
                "isometry_maps": congruence[
                    "exact_corner_isometry_maps_on_canonical_classes"
                ],
                "non_s4_maps": congruence["non_S4_corner_isometry_map_count"],
                "positive_covers": exact_cover["positive_classes"],
                "elapsed_seconds": round(elapsed, 3),
                "errors": errors[:10],
            },
            indent=2,
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="rebuild in memory and require byte equality with --out",
    )
    parser.add_argument("--print-environment", action="store_true")
    args = parser.parse_args()
    if args.print_environment:
        print(
            json.dumps(
                {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "executable": sys.executable,
                },
                indent=2,
            )
        )
    result = build_result()
    rendered = render_json(result)
    if args.check_only:
        if not args.out.exists():
            print(f"missing output for check-only: {args.out}", file=sys.stderr)
            return 1
        if args.out.read_bytes() != rendered:
            print(f"byte mismatch: {args.out}", file=sys.stderr)
            return 1
        print(f"BYTE_EXACT_PASS {sha256_file(args.out)}")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(rendered)
        print(f"WROTE {args.out}")
        print(f"RAW_SHA256 {sha256_file(args.out)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
