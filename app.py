#!/usr/bin/env python3
"""Evidence extraction prototype. The offline demo is entirely synthetic."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

VERSION = "0.1.0"
FIELDS = (
    "stabilizer", "oil_phase", "ph_condition", "droplet_size",
    "stability_observation", "magnetic_response", "cargo_release",
)
ROOT = Path(__file__).resolve().parent
MAX_SOURCE_CHARS = 80_000
PATTERNS = {
    "stabilizer": r"\b(?:iron oxide[- ]chitosan|chitosan[- ]alginate|chitosan|silica)\b",
    "oil_phase": r"\b(?:sunflower oil|liquid paraffin|olive oil|palm oil)\b",
    "ph_condition": r"\bpH\s*(?:of\s+)?\d+(?:\.\d+)?(?:\s*(?:to|[-–])\s*\d+(?:\.\d+)?)?",
    "droplet_size": r"\bdroplet(?:s)?\s+(?:(?:diameter|size)\s+)?(?:was|were|of|:)\s*\d+(?:\.\d+)?\s*(?:±\s*\d+(?:\.\d+)?\s*)?(?:μm|µm|um|nm)\b",
    "stability_observation": r"\b(?:remained stable|phase separation|coalescence|creaming)\b",
    "magnetic_response": r"\b(?:magnetic attraction|magnetic field|magnetically responsive)\b",
    "cargo_release": r"\b(?:released|release of)\s+\d+(?:\.\d+)?\s*%",
}


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(value: str | None) -> str | None:
    return None if value is None else " ".join(value.casefold().split())


def load_documents(path: Path) -> list[dict[str, Any]]:
    documents, seen = [], set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on input line {line_number}.") from exc
        if not isinstance(doc, dict):
            raise ValueError(f"Input line {line_number} must be an object.")
        for key in ("id", "title", "text", "data_kind"):
            if not isinstance(doc.get(key), str) or not doc[key].strip():
                raise ValueError(f"Document on line {line_number} needs nonempty {key}.")
        if doc["id"] in seen:
            raise ValueError(f"Duplicate document ID: {doc['id']}.")
        if doc["data_kind"] not in {"synthetic", "published", "user_owned"}:
            raise ValueError("data_kind must be synthetic, published, or user_owned.")
        if doc["data_kind"] == "published" and not doc.get("source_url"):
            raise ValueError("Published sources require source_url for traceability.")
        if len(doc["text"]) > MAX_SOURCE_CHARS:
            raise ValueError(f"Document {doc['id']} exceeds {MAX_SOURCE_CHARS} characters. Split it first.")
        seen.add(doc["id"])
        documents.append(doc)
    if not documents:
        raise ValueError("Input contains no documents.")
    return documents


def sentence_span(text: str, start: int, end: int) -> str:
    """Keep decimal points inside sentences; quotations remain exact source slices."""
    boundaries = list(re.finditer(r"[.!?](?=\s|$)|\n", text))
    left = max((m.end() for m in boundaries if m.end() <= start), default=0)
    right = min((m.end() for m in boundaries if m.start() >= end), default=len(text))
    return text[left:right].strip()


def extract_baseline(text: str) -> dict[str, dict[str, Any]]:
    result = {}
    for field, pattern in PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        result[field] = (
            {"value": match.group(0), "quote": sentence_span(text, *match.span())}
            if match else {"value": None, "quote": None}
        )
    return result


def parse_model_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        result = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned invalid JSON. No automatic paid retry was made.") from exc
    if not isinstance(result, dict):
        raise ValueError("Claude output must be a JSON object.")
    return result


def validate_extraction(text: str, candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Check shape and literal provenance, not scientific correctness or entailment."""
    if not isinstance(candidate, dict) or set(candidate) != set(FIELDS):
        raise ValueError("Extraction must contain exactly the seven documented fields.")
    result = {}
    for field in FIELDS:
        item = candidate[field]
        if not isinstance(item, dict) or set(item) != {"value", "quote"}:
            raise ValueError(f"{field} must contain exactly value and quote.")
        value, quote = item["value"], item["quote"]
        if value is None and quote is None:
            result[field] = {"value": None, "quote": None, "start": None, "end": None, "status": "not_extracted"}
            continue
        if not isinstance(value, str) or not value.strip() or not isinstance(quote, str) or not quote.strip():
            raise ValueError(f"{field}: value and quote must both be strings, or both null.")
        if quote not in text:
            raise ValueError(f"{field}: supporting quote does not occur in the source.")
        if value not in quote:
            raise ValueError(f"{field}: value must be copied verbatim from its supporting quote.")
        start = text.index(quote)
        result[field] = {"value": value, "quote": quote, "start": start, "end": start + len(quote), "status": "needs_review"}
    return result


def extract_claude(text: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError("Set ANTHROPIC_API_KEY in your environment for Claude mode.")
    if not model:
        raise ValueError("Set ANTHROPIC_MODEL or supply --model using a currently available API model ID.")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise ValueError("Install the optional Claude dependency: pip install -r requirements-claude.txt") from exc
    prompt = (ROOT / "prompts" / "extract.txt").read_text(encoding="utf-8")
    # Disable SDK retries: one invocation makes at most one paid API request per document.
    client = Anthropic(max_retries=0, timeout=45.0)
    message = client.messages.create(
        model=model, max_tokens=3000, system=prompt,
        messages=[{"role": "user", "content": json.dumps({"source_text": text}, ensure_ascii=False)}],
    )
    if message.stop_reason != "end_turn":
        raise ValueError(f"Claude response stopped with {message.stop_reason}; extraction was not accepted.")
    response = "\n".join(block.text for block in message.content if block.type == "text")
    usage = {key: getattr(message.usage, key, None) for key in ("input_tokens", "output_tokens")}
    return parse_model_json(response), {"model": message.model, "usage": usage}


def run_extraction(documents: list[dict[str, Any]], provider: str, model: str = "") -> list[dict[str, Any]]:
    if provider not in {"baseline", "claude"}:
        raise ValueError("Unknown extraction provider.")
    records = []
    for doc in documents:
        metadata = {"model": "regex-v1", "usage": None}
        if provider == "claude":
            candidate, metadata = extract_claude(doc["text"], model)
        else:
            candidate = extract_baseline(doc["text"])
        records.append({
            "document_id": doc["id"], "title": doc["title"],
            "data_kind": doc["data_kind"], "source_url": doc.get("source_url"),
            "source_sha256": fingerprint(doc["text"]), "source_text": doc["text"],
            "software_version": VERSION, "provider": provider,
            "prompt_sha256": fingerprint((ROOT / "prompts" / "extract.txt").read_text(encoding="utf-8")) if provider == "claude" else None,
            **metadata, "fields": validate_extraction(doc["text"], candidate),
        })
    return records


def write_outputs(records: list[dict[str, Any]], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "results.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8",
    )
    with (destination / "evidence.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["document_id", "data_kind", "field", "value", "quote", "start", "end", "status", "source_sha256"])
        writer.writeheader()
        for record in records:
            for field, item in record["fields"].items():
                row = {"document_id": record["document_id"], "data_kind": record["data_kind"], "field": field, **item, "source_sha256": record["source_sha256"]}
                # Preserve exact data in JSON; protect CSV viewers from formula-like source text.
                writer.writerow({key: ("'" + val if isinstance(val, str) and val.lstrip().startswith(("=", "+", "-", "@")) else val) for key, val in row.items()})
    lines = ["# Emulsion Evidence Lab: extraction report", "", "Literal source checks are automatic. Scientific interpretation still needs human review.", ""]
    cards = []
    for record in records:
        lines.extend([f"## {record['document_id']} ({record['data_kind']})", "", f"Provider: {record['provider']}; model: {record['model']}.", ""])
        cells = []
        for field, item in record["fields"].items():
            value = item["value"] or "Not extracted"
            lines.append(f"- {field}: {value} [{item['status']}]")
            quote = html.escape(item["quote"] or "No supporting passage extracted.")
            cells.append(f'<tr><th scope="row">{html.escape(field.replace("_", " "))}</th><td>{html.escape(value)}</td><td><details><summary>{html.escape(item["status"])}</summary><blockquote>{quote}</blockquote><p>Characters: {item["start"]} to {item["end"]}</p></details></td></tr>')
        lines.append("")
        cards.append(f'<article><p class="badge">{html.escape(record["data_kind"].upper())} · {html.escape(record["provider"])}</p><h2>{html.escape(record["document_id"])}: {html.escape(record["title"])}</h2><table><thead><tr><th>Field</th><th>Extracted value</th><th>Evidence</th></tr></thead><tbody>{"".join(cells)}</tbody></table><details><summary>Read source text</summary><pre>{html.escape(record["source_text"])}</pre></details></article>')
    (destination / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    banner = "SYNTHETIC SOFTWARE DEMO. These observations are invented test fixtures." if all(r["data_kind"] == "synthetic" for r in records) else "Research review. All extracted observations require human verification."
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Emulsion Evidence Lab</title><style>
body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#eff5f4;color:#16302a}main{max-width:1080px;margin:auto;padding:36px 20px}h1{font-size:36px;line-height:1.2}article{background:white;padding:24px;border:1px solid #cadcd6;border-radius:14px;margin:24px 0}table{width:100%;border-collapse:collapse}th,td{padding:12px;text-align:left;border-bottom:1px solid #e1eae7;vertical-align:top}th{font-weight:600}blockquote{margin:12px 0;padding:10px;border-left:3px solid #467867;background:#f4f8f6}pre{white-space:pre-wrap;word-break:break-word;font:inherit}input{padding:12px;width:100%;box-sizing:border-box;font:inherit;border:1px solid #8ea79f;border-radius:8px}.notice{padding:16px;background:#fff1c8;border-radius:8px}.badge{color:#467867;font-size:12px;letter-spacing:1px}summary{cursor:pointer;color:#235c48}footer{color:#466259}td{overflow-wrap:anywhere}@media(max-width:650px){table{font-size:13px}th,td{padding:8px}article{padding:12px}h1{font-size:28px}}</style><main><p class="badge">REPRODUCIBLE RESEARCH PROTOTYPE · VERSION 0.1.0</p><h1>Emulsion Evidence Lab</h1><p>Inspect extracted observations and their source passages.</p><p class="notice">BANNER</p><label for="query">Filter documents and observations</label><input id="query" type="search" placeholder="Try: droplet, synthetic-003, magnetic"><section>CARDS</section><footer>Exact quotation checks establish provenance. They do not establish scientific correctness. Character offsets use Python Unicode indices, with an exclusive end.</footer></main><script>document.getElementById('query').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('article').forEach(a=>a.hidden=!a.textContent.toLowerCase().includes(q));});</script></html>'''
    (destination / "review.html").write_text(page.replace("BANNER", html.escape(banner)).replace("CARDS", "".join(cards)), encoding="utf-8")


def evaluate_records(records: list[dict[str, Any]], gold: dict[str, Any]) -> dict[str, Any]:
    if not records or len({r["document_id"] for r in records}) != len(records):
        raise ValueError("Evaluation needs unique, nonempty prediction records.")
    if set(gold) != {r["document_id"] for r in records}:
        raise ValueError("Gold and predictions must contain exactly the same document IDs.")
    exact = tp = fp = fn = tn = present = 0
    by_field = {field: {"exact": 0, "total": 0} for field in FIELDS}
    mismatches = []
    for record in records:
        expected = gold[record["document_id"]]
        if not isinstance(expected, dict) or set(expected) != set(FIELDS) or any(v is not None and not isinstance(v, str) for v in expected.values()):
            raise ValueError("Every gold document must specify the seven fields as strings or null.")
        if fingerprint(record["source_text"]) != record["source_sha256"]:
            raise ValueError("Prediction source hash does not match source text.")
        candidate = {field: {key: record["fields"][field][key] for key in ("value", "quote")} for field in FIELDS}
        checked = validate_extraction(record["source_text"], candidate)
        if checked != record["fields"]:
            raise ValueError("Prediction evidence offsets or review status have changed.")
        for field in FIELDS:
            predicted = record["fields"][field]["value"]
            correct = normalize(predicted) == normalize(expected[field])
            exact += int(correct)
            by_field[field]["exact"] += int(correct)
            by_field[field]["total"] += 1
            if predicted is not None:
                present += 1
                if correct:
                    tp += 1
                else:
                    fp += 1
            if expected[field] is not None and not correct:
                fn += 1
            if expected[field] is None and predicted is None:
                tn += 1
            if not correct:
                mismatches.append({"document_id": record["document_id"], "field": field, "expected": expected[field], "predicted": predicted})
    total = len(records) * len(FIELDS)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {
        "evaluation_scope": "synthetic_smoke_test" if all(r["data_kind"] == "synthetic" for r in records) else "user_supplied_gold",
        "documents": len(records), "fields_total": total, "field_exact_match": exact / total,
        "non_null_precision": precision, "non_null_recall": recall, "non_null_f1": f1,
        "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_null": tn,
        "literal_quote_check_rate": 1.0 if present else None,
        "quote_check_note": "Accepted predictions only; this does not measure rejected responses or semantic support.",
        "by_field": by_field, "mismatches": mismatches,
        "limitation": "Small synthetic fixture scores measure software behaviour, not real-paper extraction accuracy or Claude performance.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="Extract observations into a review bundle.")
    extract.add_argument("--input", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)
    extract.add_argument("--provider", choices=["baseline", "claude"], default="baseline")
    extract.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", ""))
    extract.add_argument("--limit", type=int, default=None)
    evaluate = commands.add_parser("evaluate", help="Compare accepted predictions with a user-supplied gold file.")
    evaluate.add_argument("--predictions", type=Path, required=True)
    evaluate.add_argument("--gold", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            documents = load_documents(args.input)
            if args.limit is not None:
                if args.limit < 1:
                    raise ValueError("--limit must be at least 1.")
                documents = documents[:args.limit]
            if args.provider == "claude":
                print(f"Claude mode: up to {len(documents)} paid requests, with automatic retries disabled.", file=sys.stderr)
            records = run_extraction(documents, args.provider, args.model)
            write_outputs(records, args.output)
            print(f"Wrote {len(records)} documents to {args.output}.")
        else:
            records = [json.loads(line) for line in args.predictions.read_text(encoding="utf-8").splitlines() if line.strip()]
            metrics = evaluate_records(records, json.loads(args.gold.read_text(encoding="utf-8")))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"{metrics['evaluation_scope']}: exact field match {metrics['field_exact_match']:.1%}. See {args.output}.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Provider exception messages may contain source text. Print only their class.
        print(f"Provider failed ({type(exc).__name__}); no automatic paid retry was made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
