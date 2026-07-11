from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicPackageTests(unittest.TestCase):
    def test_quick_verifier_executes(self):
        completed = subprocess.run(
            [sys.executable, "-B", "scripts/verify_public_package.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PUBLIC_QUICK_VERIFY_PASS", completed.stdout)

    def test_row_joins_and_masks(self):
        atlas = json.loads((ROOT / "artifacts/nonconvex_tile_atlas.json").read_text(encoding="utf-8"))
        covers = json.loads((ROOT / "artifacts/cover_atlas.json").read_text(encoding="utf-8"))
        ambient = json.loads((ROOT / "artifacts/ambient_symmetry_atlas.json").read_text(encoding="utf-8"))
        ids = [row["row_id"] for row in atlas["rows"]]
        self.assertEqual(len(ids), 82)
        self.assertEqual(len(set(ids)), 82)
        self.assertEqual(set(ids), {row["row_id"] for row in covers["rows"]})
        self.assertEqual(set(ids), {row["row_id"] for row in ambient["rows"]})
        self.assertTrue(all(row["facet_connected"] for row in atlas["rows"]))
        self.assertTrue(all(not row["halfspace_convex"] for row in atlas["rows"]))
        self.assertTrue(all(row["left_translate_tiler"] for row in atlas["rows"]))

    def test_public_full_replay_is_standalone(self):
        script = (ROOT / "scripts/verify_global_congruence.py").read_text(encoding="utf-8")
        self.assertIn('ROOT / "scripts" / "geometry_core.py"', script)
        self.assertIn('ROOT / "data" / "bounded_census_source.json"', script)
        self.assertNotIn("ambient_congruence_and_transitivity", script)

    def test_latex_artifact_references_exist(self):
        pattern = re.compile(r"artifacts/[A-Za-z0-9_.-]+[.]json")
        references = set()
        for path in (ROOT / "paper").rglob("*.tex"):
            references.update(pattern.findall(path.read_text(encoding="utf-8")))
        self.assertTrue(references)
        missing = [rel for rel in sorted(references) if not (ROOT / rel).is_file()]
        self.assertEqual(missing, [])

    def test_public_status_metadata_is_current(self):
        theorem = json.loads((ROOT / "certificates/THEOREM_REPLAY_CERTIFICATE.json").read_text(encoding="utf-8"))
        preflight = json.loads((ROOT / "certificates/PACKAGE_PREFLIGHT_CERTIFICATE.json").read_text(encoding="utf-8"))
        self.assertTrue(theorem["public_repository_active"])
        self.assertTrue(theorem["external_red_team_complete"])
        self.assertFalse(theorem["archival_article_release_authorized"])
        self.assertTrue(preflight["public_repository_active"])
        self.assertTrue(preflight["checks"]["external_red_team_complete"])
        self.assertFalse(preflight["archival_article_release_authorized"])
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn('version: "1.0.0"', cff)
        self.assertIn("Congruence Rigidity, Exact Covers, and Patterson Separation", cff)
        public_text = " ".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "README.md",
                "README_REVIEWER.md",
                "paper/main.tex",
                "paper/sections/10_reproducibility.tex",
            )
        )
        for stale in (
            "external red-team record and owner release decision are added",
            "after the final external red team",
            "the package becomes a publication",
        ):
            self.assertNotIn(stale, public_text)


if __name__ == "__main__":
    unittest.main()
