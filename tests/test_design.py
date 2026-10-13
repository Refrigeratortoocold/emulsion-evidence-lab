import copy
import csv
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.config = app.load_reference()
        self.assay = app.ROOT / "data/synthetic_assay.csv"
        self.candidates = app.prepare_benchmark(self.assay, self.config, 20, 42, "synthetic")

    def test_exact_reference_and_protected_motif(self):
        self.assertEqual(len(self.config["reference_sequence"]), 238)
        self.assertEqual(self.config["reference_sequence"][64:67], "SYG")
        self.assertEqual(self.config["reference_sequence"][63], "L")

    def test_substitution_applied_and_canonicalised(self):
        result = app.make_variant("E6D:K3R", self.config)
        self.assertEqual(result["mutations"], "K3R:E6D")
        self.assertEqual(result["sequence"][2], "R")
        self.assertEqual(result["sequence"][5], "D")
        self.assertEqual(len(result["sequence"]), 238)

    def test_wrong_reference_residue_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "reference residue"):
            app.make_variant("A3R", self.config)

    def test_protected_chromophore_cannot_be_changed(self):
        with self.assertRaisesRegex(ValueError, "protected motif"):
            app.make_variant("S65A", self.config)

    def test_duplicate_position_invalid_alphabet_and_no_change(self):
        for descriptor in ("K3R:K3A", "K3X", "K3K", "K0R", "K999R", "K3del"):
            with self.subTest(descriptor=descriptor), self.assertRaises(ValueError):
                app.make_variant(descriptor, self.config)

    def test_mutation_budget_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            app.make_variant("K3R:E6D:G10A:V12I", self.config)

    def test_seeded_proposals_are_valid_and_reproducible(self):
        first = app.propose(self.config, "random", 30, 8)
        second = app.propose(self.config, "random", 30, 8)
        self.assertEqual(first, second)
        self.assertEqual(first["accepted_count"], 30)
        self.assertEqual(len({item["variant_id"] for item in first["variants"]}), 30)
        self.assertTrue(all(item["sequence"][64:67] == "SYG" for item in first["variants"]))

    def test_preparation_withholds_labels_and_records_exclusions(self):
        self.assertEqual(self.candidates["assay_rows"], 9)
        self.assertEqual(self.candidates["eligible_rows"], 8)
        self.assertEqual(self.candidates["excluded_rows"], 1)
        self.assertTrue(all("DMS_score" not in item for item in self.candidates["variants"]))

    def test_label_changes_do_not_change_candidate_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "changed.csv"
            with self.assay.open() as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row["DMS_score"] = "100"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            changed = app.prepare_benchmark(path, self.config, 20, 42, "synthetic")
        self.assertEqual(changed["variants"], self.candidates["variants"])
        self.assertNotEqual(changed["assay_sha256"], self.candidates["assay_sha256"])

    def test_measured_label_in_ranking_input_is_rejected(self):
        self.candidates["variants"][0]["DMS_score"] = 999
        with self.assertRaisesRegex(ValueError, "Measured labels"):
            app.rank_candidates(self.candidates, self.config, "distance", 42)

    def test_inconsistent_sequence_or_id_is_rejected(self):
        for field, value in (("sequence", "AAAA"), ("variant_id", "invented")):
            document = copy.deepcopy(self.candidates)
            document["variants"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                app.validate_candidates(document, self.config)

    def test_spearman_handles_ties_and_constant_scores(self):
        self.assertAlmostEqual(app.spearman([10, 10, 20], [1, 2, 3]), math.sqrt(3) / 2)
        self.assertIsNone(app.spearman([1, 1, 1], [1, 2, 3]))
        self.assertAlmostEqual(app.spearman([3, 2, 1], [1, 2, 3]), -1)

    def test_ideal_ranking_has_ndcg_one(self):
        ranking = app.rank_candidates(self.candidates, self.config, "distance", 42)
        records, _ = app.load_assay(self.assay, self.config)
        labels = {item["variant_id"]: item["DMS_score"] for item in records}
        for item in ranking["variants"]:
            item["predicted_score"] = labels[item["variant_id"]]
        metrics = app.evaluate_ranking(ranking, self.assay, self.config, 3, None)
        self.assertEqual(metrics["evaluation_kind"], "synthetic_software_test")
        self.assertEqual(metrics["ndcg_at_k"], 1)
        self.assertAlmostEqual(metrics["spearman"], 1)

    def test_changed_assay_hash_is_rejected(self):
        ranking = app.rank_candidates(self.candidates, self.config, "random", 42)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "changed.csv"
            path.write_text(self.assay.read_text().replace("3.1", "3.2"))
            with self.assertRaisesRegex(ValueError, "changed"):
                app.evaluate_ranking(ranking, path, self.config, 3, None)

    def test_unmeasured_proposals_cannot_receive_invented_assay_labels(self):
        proposals = app.propose(self.config, "random", 2, 42)
        ranking = app.rank_candidates(proposals, self.config, "distance", 42)
        with self.assertRaisesRegex(ValueError, "observed assay score"):
            app.evaluate_ranking(ranking, self.assay, self.config, 2, None)

    def test_duplicate_or_nonfinite_claude_scores_are_rejected(self):
        batch = self.candidates["variants"][:2]
        valid = [{"mutations": item["mutations"], "predicted_score": 0.5, "rationale": "Hypothesis", "uncertainty": "Unmeasured"} for item in batch]
        app.validate_scores({"scores": valid}, batch, self.config)
        for score in (float("nan"), float("inf"), True, 1.5):
            invalid = copy.deepcopy(valid)
            invalid[0]["predicted_score"] = score
            with self.subTest(score=score), self.assertRaisesRegex(ValueError, "finite"):
                app.validate_scores({"scores": invalid}, batch, self.config)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            app.validate_scores({"scores": [valid[0], valid[0]]}, batch, self.config)

    def test_exported_report_escapes_hypothesis_html(self):
        ranking = app.rank_candidates(self.candidates, self.config, "distance", 42)
        ranking["variants"][0]["rationale"] = "<script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            app.export_ranking(ranking, destination)
            page = (destination / "review.html").read_text()
            self.assertNotIn("<script>alert", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("SYNTHETIC SOFTWARE DEMO", page)
            self.assertEqual({p.name for p in destination.iterdir()}, {"ranking.json", "ranking.csv", "candidates.fasta", "review.html"})

    def test_claude_payload_withholds_labels_and_records_model(self):
        candidates = self.candidates["variants"]
        response = {"scores": [{"mutations": item["mutations"], "predicted_score": 0.5, "rationale": "Hypothesis", "uncertainty": "Unmeasured"} for item in candidates]}
        captured = {}
        def create(**kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(response))], model="test-model", usage=SimpleNamespace(input_tokens=123, output_tokens=45))
        def client(**kwargs):
            captured["client"] = kwargs
            return SimpleNamespace(messages=SimpleNamespace(create=create))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-test-only"}), patch.dict(sys.modules, {"anthropic": SimpleNamespace(Anthropic=client)}):
            ranking = app.rank_candidates(self.candidates, self.config, "claude", 42, "test-model")
        payload = json.loads(captured["request"]["messages"][0]["content"])
        self.assertTrue(all("DMS_score" not in item for item in payload["candidates"]))
        self.assertEqual(captured["client"]["max_retries"], 0)
        self.assertEqual(ranking["api_calls"][0]["model"], "test-model")

    def test_invalid_proposals_are_counted_without_fabricating_sequences(self):
        fake = {"variants": [{"mutations": "K3R", "rationale": "Hypothesis"}, {"mutations": "S65A", "rationale": "Invalid"}]}
        with patch.object(app, "call_claude", return_value=(fake, {"model": "test"})):
            result = app.propose(self.config, "claude", 2, 42, "test")
        self.assertEqual(result["returned_count"], 2)
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_cli_demo_completes_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(app.main(["demo", "--output", temp]), 0)
            result = json.loads((Path(temp) / "evaluation.json").read_text())
            self.assertEqual(result["evaluated_candidates"], 8)
            self.assertEqual(result["evaluation_kind"], "synthetic_software_test")


if __name__ == "__main__":
    unittest.main()
