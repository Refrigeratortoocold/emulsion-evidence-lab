import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.documents = app.load_documents(app.ROOT / "data/demo_documents.jsonl")
        self.gold = json.loads((app.ROOT / "data/demo_gold.json").read_text())

    def test_full_offline_pipeline_and_gold(self):
        records = app.run_extraction(self.documents, "baseline")
        metrics = app.evaluate_records(records, self.gold)
        self.assertEqual(metrics["evaluation_scope"], "synthetic_smoke_test")
        self.assertEqual(metrics["fields_total"], 28)
        self.assertEqual(metrics["field_exact_match"], 1.0)
        self.assertEqual(metrics["false_positive"], 0)
        self.assertEqual(metrics["false_negative"], 0)

    def test_nanoparticle_size_is_not_droplet_size(self):
        values = app.extract_baseline("Silica particle diameter was 90 nm. Mean droplet diameter was 3.8 um.")
        self.assertEqual(values["droplet_size"]["value"], "droplet diameter was 3.8 um")

    def test_missing_fields_are_null(self):
        values = app.extract_baseline(self.documents[-1]["text"])
        self.assertTrue(all(item == {"value": None, "quote": None} for item in values.values()))

    def test_decimal_does_not_break_supporting_sentence(self):
        text = "The sample was prepared at pH 5.2. Another sentence."
        item = app.extract_baseline(text)["ph_condition"]
        self.assertEqual(item["quote"], "The sample was prepared at pH 5.2.")

    def test_fabricated_quote_is_rejected(self):
        text = self.documents[0]["text"]
        candidate = app.extract_baseline(text)
        candidate["oil_phase"] = {"value": "olive oil", "quote": "We used olive oil."}
        with self.assertRaisesRegex(ValueError, "does not occur"):
            app.validate_extraction(text, candidate)

    def test_value_must_be_present_in_supporting_quote(self):
        text = self.documents[0]["text"]
        candidate = app.extract_baseline(text)
        candidate["oil_phase"]["value"] = "olive oil"
        with self.assertRaisesRegex(ValueError, "verbatim"):
            app.validate_extraction(text, candidate)

    def test_mixed_null_and_string_is_rejected(self):
        text = self.documents[0]["text"]
        candidate = app.extract_baseline(text)
        candidate["oil_phase"]["quote"] = None
        with self.assertRaisesRegex(ValueError, "both"):
            app.validate_extraction(text, candidate)

    def test_extra_fields_are_rejected(self):
        candidate = app.extract_baseline("Nothing reported.")
        candidate["made_up_field"] = {"value": None, "quote": None}
        with self.assertRaisesRegex(ValueError, "seven"):
            app.validate_extraction("Nothing reported.", candidate)

    def test_unicode_offsets_are_exact(self):
        text = "观察。 Mean droplet diameter was 2.9 μm."
        candidate = app.extract_baseline(text)
        item = app.validate_extraction(text, candidate)["droplet_size"]
        self.assertEqual(text[item["start"]:item["end"]], item["quote"])

    def test_source_changes_break_evaluation(self):
        records = app.run_extraction(self.documents, "baseline")
        records[0]["source_text"] += "changed"
        with self.assertRaisesRegex(ValueError, "hash"):
            app.evaluate_records(records, self.gold)

    def test_offsets_cannot_be_silently_changed(self):
        records = app.run_extraction(self.documents, "baseline")
        records[0]["fields"]["oil_phase"]["start"] += 1
        with self.assertRaisesRegex(ValueError, "offsets"):
            app.evaluate_records(records, self.gold)

    def test_wrong_non_null_value_counts_as_fp_and_fn(self):
        records = app.run_extraction(self.documents, "baseline")
        gold = copy.deepcopy(self.gold)
        gold["synthetic-001"]["oil_phase"] = "olive oil"
        metrics = app.evaluate_records(records, gold)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertEqual(metrics["false_negative"], 1)

    def test_zero_f1_for_entirely_missed_observation(self):
        doc = {"id": "missing", "title": "fixture", "text": "Nothing reported.", "data_kind": "synthetic"}
        records = app.run_extraction([doc], "baseline")
        gold = {"missing": {field: None for field in app.FIELDS}}
        gold["missing"]["oil_phase"] = "sunflower oil"
        metrics = app.evaluate_records(records, gold)
        self.assertEqual(metrics["non_null_f1"], 0.0)

    def test_evaluation_rejects_missing_gold_document(self):
        records = app.run_extraction(self.documents, "baseline")
        del self.gold["synthetic-004"]
        with self.assertRaisesRegex(ValueError, "same document IDs"):
            app.evaluate_records(records, self.gold)

    def test_duplicate_document_ids_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.jsonl"
            path.write_text((json.dumps(self.documents[0]) + "\n") * 2)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                app.load_documents(path)

    def test_published_document_needs_source_url(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.jsonl"
            doc = {**self.documents[0], "data_kind": "published"}
            path.write_text(json.dumps(doc) + "\n")
            with self.assertRaisesRegex(ValueError, "source_url"):
                app.load_documents(path)

    def test_review_report_escapes_source_html(self):
        doc = {"id": "<script>alert(1)</script>", "title": "<img onerror=alert(1)>", "data_kind": "synthetic", "text": "<script>alert(2)</script> Chitosan stabilized olive oil."}
        with tempfile.TemporaryDirectory() as temp:
            app.write_outputs(app.run_extraction([doc], "baseline"), Path(temp))
            page = (Path(temp) / "review.html").read_text()
            self.assertNotIn("<script>alert", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("SYNTHETIC SOFTWARE DEMO", page)

    def test_exports_preserve_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            records = app.run_extraction(self.documents, "baseline")
            app.write_outputs(records, output)
            self.assertEqual({p.name for p in output.iterdir()}, {"results.jsonl", "evidence.csv", "report.md", "review.html"})
            first = json.loads((output / "results.jsonl").read_text().splitlines()[0])
            self.assertEqual(first["source_sha256"], app.fingerprint(self.documents[0]["text"]))

    def test_invalid_model_json_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            app.parse_model_json("Here is an invented observation.")

    def test_missing_api_key_fails_before_call(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "ANTHROPIC_API_KEY"):
                app.extract_claude("source", "test-model")

    def test_mocked_claude_uses_configured_model_and_logs_usage(self):
        candidate = app.extract_baseline(self.documents[0]["text"])
        calls = {}
        def create(**kwargs):
            calls["request"] = kwargs
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(candidate))], usage=SimpleNamespace(input_tokens=123, output_tokens=45), model="test-model")
        def client(**kwargs):
            calls["client"] = kwargs
            return SimpleNamespace(messages=SimpleNamespace(create=create))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-test-only"}), patch.dict(sys.modules, {"anthropic": SimpleNamespace(Anthropic=client)}):
            values, metadata = app.extract_claude(self.documents[0]["text"], "test-model")
        self.assertEqual(calls["request"]["model"], "test-model")
        self.assertEqual(calls["client"]["max_retries"], 0)
        self.assertEqual(metadata["usage"]["input_tokens"], 123)
        app.validate_extraction(self.documents[0]["text"], values)

    def test_truncated_claude_response_is_not_accepted(self):
        response = SimpleNamespace(stop_reason="max_tokens")
        fake = SimpleNamespace(Anthropic=lambda **kw: SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: response)))
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fake-test-only"}), patch.dict(sys.modules, {"anthropic": fake}):
            with self.assertRaisesRegex(ValueError, "not accepted"):
                app.extract_claude("source", "test-model")

    def test_quote_presence_does_not_prove_semantic_support(self):
        # This intentionally passes the mechanical check. Human review must catch it.
        text = "Olive oil was not used in the experiment."
        candidate = {field: {"value": None, "quote": None} for field in app.FIELDS}
        candidate["oil_phase"] = {"value": "Olive oil", "quote": text}
        result = app.validate_extraction(text, candidate)
        self.assertEqual(result["oil_phase"]["status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
