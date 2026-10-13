#!/usr/bin/env python3
"""Constrained GFP variant design and assay-based ranking evaluation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parent
AA = "ACDEFGHIKLMNPQRSTVWY"
VERSION = "0.2.0"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_reference(path: Path = ROOT / "data/reference.json") -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    sequence = config["reference_sequence"]
    if len(sequence) != config["sequence_length"] or not set(sequence) <= set(AA):
        raise ValueError("Reference sequence has an invalid length or alphabet.")
    if "".join(sequence[p - 1] for p in config["protected_positions"]) != config["protected_motif"]:
        raise ValueError("Protected motif does not match the reference sequence.")
    config["reference_sha256"] = digest(sequence)
    return config


def make_variant(descriptor: str, config: dict, enforce_design: bool = True) -> dict:
    """Validate substitutions against the exact assay reference, using 1-based positions."""
    if not isinstance(descriptor, str) or not descriptor:
        raise ValueError("A nonempty substitution descriptor is required.")
    sequence = list(config["reference_sequence"])
    mutations, positions = [], set()
    for token in descriptor.split(":"):
        match = re.fullmatch(r"([ACDEFGHIKLMNPQRSTVWY])([1-9][0-9]*)([ACDEFGHIKLMNPQRSTVWY])", token)
        if not match:
            raise ValueError(f"Invalid substitution: {token}.")
        original, pos_text, replacement = match.groups()
        position = int(pos_text)
        if position > len(sequence) or position in positions:
            raise ValueError("Substitution position is out of range or duplicated.")
        if config["reference_sequence"][position - 1] != original:
            raise ValueError(f"{token} does not match the assay reference residue.")
        if original == replacement:
            raise ValueError("A substitution must change the residue.")
        if enforce_design and (position in config["protected_positions"] or not config["allowed_position_start"] <= position <= config["allowed_position_end"]):
            raise ValueError("Substitution violates the configured design region or protected motif.")
        positions.add(position)
        mutations.append((position, token))
        sequence[position - 1] = replacement
    if enforce_design and len(mutations) > config["max_mutations"]:
        raise ValueError("Variant exceeds the mutation budget.")
    canonical = ":".join(token for _, token in sorted(mutations))
    return {"variant_id": canonical, "mutations": canonical, "sequence": "".join(sequence), "mutation_count": len(mutations)}


def validate_candidates(document: dict, config: dict) -> list[dict]:
    if document.get("reference_sha256") != config["reference_sha256"] or document.get("assay_id") != config["assay_id"]:
        raise ValueError("Candidate provenance does not match the configured assay reference.")
    if not isinstance(document.get("variants"), list) or not document["variants"]:
        raise ValueError("Candidate document must contain a nonempty variants list.")
    candidates, seen = [], set()
    for item in document["variants"]:
        if not isinstance(item, dict):
            raise ValueError("Each candidate must be an object.")
        if any(key in item for key in ("DMS_score", "observed_score", "assay_score")):
            raise ValueError("Measured labels must not enter the candidate-ranking input.")
        candidate = make_variant(item.get("mutations"), config)
        if item.get("variant_id", candidate["variant_id"]) != candidate["variant_id"]:
            raise ValueError("Candidate ID disagrees with its canonical substitutions.")
        if item.get("sequence", candidate["sequence"]) != candidate["sequence"]:
            raise ValueError("Candidate sequence disagrees with its substitutions.")
        if candidate["variant_id"] in seen:
            raise ValueError("Duplicate candidate after canonicalising substitutions.")
        seen.add(candidate["variant_id"])
        candidates.append(candidate)
    return candidates


def call_claude(task: str, payload: dict, model: str) -> tuple[dict, dict]:
    if not os.environ.get("ANTHROPIC_API_KEY") or not model:
        raise ValueError("Claude mode requires ANTHROPIC_API_KEY and ANTHROPIC_MODEL or --model.")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise ValueError("Install the optional dependency with pip install -r requirements-claude.txt.") from exc
    prompt = (ROOT / "prompts" / f"{task}.txt").read_text(encoding="utf-8")
    response = Anthropic(max_retries=0, timeout=45.0).messages.create(
        model=model, max_tokens=5000, system=prompt,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"Incomplete Claude response: {response.stop_reason}.")
    raw = "\n".join(block.text for block in response.content if block.type == "text").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Claude must return a JSON object.")
    return parsed, {"model": response.model, "prompt_sha256": digest(prompt), "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}


def propose(config: dict, provider: str, count: int, seed: int, model: str = "") -> dict:
    if not 1 <= count <= 100:
        raise ValueError("Proposal count must be between 1 and 100.")
    metadata, raw = [], []
    if provider == "claude":
        response, trace = call_claude("propose", {"reference": config, "requested_count": count, "objective": "Prioritise variants for retained or increased GFP fluorescence; this is an unvalidated computational proposal."}, model)
        raw = response.get("variants")
        metadata.append(trace)
        if not isinstance(raw, list) or len(raw) > count:
            raise ValueError("Claude proposal response has an invalid variants list.")
    elif provider == "random":
        rng = random.Random(seed)
        eligible = [p for p in range(config["allowed_position_start"], config["allowed_position_end"] + 1) if p not in config["protected_positions"]]
        seen = set()
        while len(raw) < count:
            positions = sorted(rng.sample(eligible, rng.randint(1, config["max_mutations"])))
            tokens = [f"{config['reference_sequence'][p - 1]}{p}{rng.choice(AA.replace(config['reference_sequence'][p - 1], ''))}" for p in positions]
            descriptor = ":".join(tokens)
            if descriptor not in seen:
                seen.add(descriptor)
                raw.append({"mutations": descriptor, "rationale": "Uniform random proposal under the configured sequence constraints."})
    else:
        raise ValueError("Unknown proposal provider.")
    accepted, rejected, seen = [], [], set()
    for index, item in enumerate(raw):
        try:
            if not isinstance(item, dict):
                raise ValueError("Proposal must be an object.")
            candidate = make_variant(item.get("mutations"), config)
            if candidate["variant_id"] in seen:
                raise ValueError("Duplicate proposal.")
            rationale = item.get("rationale", "No rationale supplied.")
            if not isinstance(rationale, str) or len(rationale) > 2000:
                raise ValueError("Rationale must be text of at most 2000 characters.")
            seen.add(candidate["variant_id"])
            accepted.append({**candidate, "rationale": rationale, "biological_validation": "unmeasured"})
        except ValueError as exc:
            rejected.append({"proposal_index": index, "reason": str(exc)})
    return {"software_version": VERSION, "assay_id": config["assay_id"], "reference_sha256": config["reference_sha256"], "data_kind": "unmeasured_design", "provider": provider, "seed": seed if provider == "random" else None, "requested_count": count, "returned_count": len(raw), "accepted_count": len(accepted), "rejected": rejected, "api_calls": metadata, "variants": accepted}


def load_assay(path: Path, config: dict) -> tuple[list[dict], str]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if not {"mutant", "mutated_sequence", "DMS_score"} <= set(reader.fieldnames or []):
        raise ValueError("Assay CSV requires mutant, mutated_sequence and DMS_score columns.")
    records, seen = [], set()
    for row in reader:
        variant = make_variant(row["mutant"], config, enforce_design=False)
        score = float(row["DMS_score"])
        if not math.isfinite(score) or row["mutated_sequence"] != variant["sequence"]:
            raise ValueError("Assay score is non-finite, or its sequence does not match the reference.")
        if variant["variant_id"] in seen:
            raise ValueError("Assay has duplicate canonical variants. Aggregate replicates explicitly first.")
        seen.add(variant["variant_id"])
        records.append({**variant, "DMS_score": score})
    if not records:
        raise ValueError("Assay CSV is empty.")
    return records, digest(text)


def prepare_benchmark(path: Path, config: dict, count: int, seed: int, data_kind: str) -> dict:
    if count < 1 or data_kind not in {"synthetic", "published"}:
        raise ValueError("Specify a positive count and a valid data kind.")
    records, assay_hash = load_assay(path, config)
    eligible, excluded = [], 0
    for record in records:
        try:
            eligible.append(make_variant(record["mutations"], config))
        except ValueError:
            excluded += 1
    eligible.sort(key=lambda item: item["variant_id"])
    rng = random.Random(seed)
    selected = rng.sample(eligible, min(count, len(eligible)))
    if not selected:
        raise ValueError("No assay variants meet the design constraints.")
    return {"software_version": VERSION, "assay_id": config["assay_id"], "reference_sha256": config["reference_sha256"], "data_kind": data_kind, "assay_sha256": assay_hash, "assay_rows": len(records), "eligible_rows": len(eligible), "excluded_rows": excluded, "seed": seed, "variants": selected}


def validate_scores(response: dict, batch: list[dict], config: dict) -> list[dict]:
    items = response.get("scores")
    if not isinstance(items, list) or len(items) != len(batch):
        raise ValueError("Claude must score every candidate exactly once.")
    expected = {item["variant_id"] for item in batch}
    scored, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each Claude score must be an object.")
        candidate = make_variant(item.get("mutations"), config)
        key, score = candidate["variant_id"], item.get("predicted_score")
        if key not in expected or key in seen:
            raise ValueError("Claude scored an unknown or duplicate candidate.")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Predicted scores must be finite numbers between 0 and 1.")
        rationale, uncertainty = item.get("rationale"), item.get("uncertainty")
        if not isinstance(rationale, str) or not isinstance(uncertainty, str) or len(rationale) + len(uncertainty) > 4000:
            raise ValueError("Each score needs concise rationale and uncertainty text.")
        seen.add(key)
        scored.append({**candidate, "predicted_score": score, "rationale": rationale, "uncertainty": uncertainty})
    return scored


def rank_candidates(document: dict, config: dict, provider: str, seed: int, model: str = "") -> dict:
    candidates = validate_candidates(document, config)
    scored, calls = [], []
    if provider == "claude":
        for start in range(0, len(candidates), 10):
            batch = candidates[start:start + 10]
            # Only sequence information enters the model; measured assay labels remain separate.
            response, trace = call_claude("rank", {"reference": config, "candidates": batch}, model)
            scored.extend(validate_scores(response, batch, config))
            calls.append(trace)
    elif provider in {"distance", "random"}:
        for candidate in candidates:
            score = 1 / (1 + candidate["mutation_count"]) if provider == "distance" else random.Random(f"{seed}:{candidate['variant_id']}").random()
            scored.append({**candidate, "predicted_score": score, "rationale": "Fewer-substitutions baseline." if provider == "distance" else "Seeded random ranking baseline.", "uncertainty": "This baseline does not predict fluorescence or folding."})
    else:
        raise ValueError("Unknown ranking provider.")
    scored.sort(key=lambda item: (-item["predicted_score"], item["variant_id"]))
    return {"software_version": VERSION, "assay_id": config["assay_id"], "reference_sha256": config["reference_sha256"], "assay_sha256": document.get("assay_sha256"), "data_kind": document["data_kind"], "method": provider, "seed": seed if provider != "claude" else None, "api_calls": calls, "attempted_candidates": len(candidates), "scored_candidates": len(scored), "variants": scored}


def average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def spearman(predicted: list[float], observed: list[float]) -> float | None:
    if len(predicted) != len(observed) or len(predicted) < 2:
        return None
    x, y = average_ranks(predicted), average_ranks(observed)
    mx, my = statistics.mean(x), statistics.mean(y)
    denominator = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / denominator if denominator else None


def evaluate_ranking(ranking: dict, assay_path: Path, config: dict, top_k: int, threshold: float | None) -> dict:
    if top_k < 1 or (threshold is not None and not math.isfinite(threshold)):
        raise ValueError("Use a positive top-k and a finite optional hit threshold.")
    candidates = validate_candidates(ranking, config)
    records, assay_hash = load_assay(assay_path, config)
    if ranking.get("assay_sha256") and ranking["assay_sha256"] != assay_hash:
        raise ValueError("Assay content changed after benchmark preparation.")
    labels = {item["variant_id"]: item["DMS_score"] for item in records}
    predictions = {item["variant_id"]: item["predicted_score"] for item in ranking["variants"]}
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in predictions.values()):
        raise ValueError("Ranking contains invalid predicted scores.")
    if any(candidate["variant_id"] not in labels for candidate in candidates):
        raise ValueError("Every evaluated candidate needs an observed assay score; unmeasured proposals cannot be benchmarked by guessing labels.")
    ordered = sorted(predictions, key=lambda key: (-predictions[key], key))
    observed = [labels[key] for key in ordered]
    k = min(top_k, len(ordered))
    minimum = min(observed)
    gain = [value - minimum for value in observed]
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(gain[:k]))
    ideal = sum(value / math.log2(index + 2) for index, value in enumerate(sorted(gain, reverse=True)[:k]))
    return {"evaluation_kind": "synthetic_software_test" if ranking["data_kind"] == "synthetic" else "retrospective_assay_evaluation", "assay_id": config["assay_id"], "assay_sha256": assay_hash, "method": ranking["method"], "evaluated_candidates": len(ordered), "top_k": k, "spearman": spearman([predictions[key] for key in ordered], observed), "ndcg_at_k": dcg / ideal if ideal else None, "ndcg_definition": "Linear relevance = DMS_score minus the minimum score within the evaluated candidate pool; prediction ties are broken by canonical variant ID.", "top_k_mean_DMS_score": statistics.mean(observed[:k]), "hit_threshold": threshold, "top_k_hit_rate": sum(value >= threshold for value in observed[:k]) / k if threshold is not None else None, "limitation": "Synthetic labels test software only. Retrospective results do not establish new experimental improvements, novelty, folding stability, or causal mechanisms."}


def export_ranking(ranking: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    save_json(destination / "ranking.json", ranking)
    with (destination / "ranking.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant_id", "mutation_count", "predicted_score", "sequence", "rationale", "uncertainty"])
        writer.writeheader()
        for candidate in ranking["variants"]:
            writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value) for key in writer.fieldnames for value in [candidate[key]]})
    (destination / "candidates.fasta").write_text("".join(f">{item['variant_id']} computational_candidate\n{item['sequence']}\n" for item in ranking["variants"]), encoding="utf-8")
    rows = "".join(f'<tr><td>{index}</td><td>{html.escape(item["mutations"])}</td><td>{item["predicted_score"]:.3f}</td><td><details><summary>Inspect hypothesis</summary><p>{html.escape(item["rationale"])}</p><p>{html.escape(item["uncertainty"])}</p><code>{html.escape(item["sequence"])}</code></details></td></tr>' for index, item in enumerate(ranking["variants"], 1))
    notice = "SYNTHETIC SOFTWARE DEMO. Assay labels in this example are invented." if ranking["data_kind"] == "synthetic" else "COMPUTATIONAL CANDIDATES. Predicted scores are unvalidated priorities, not measured fluorescence."
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Claude Protein Design</title><style>body{font:16px/1.6 system-ui;background:#f1f5fa;color:#172d42;margin:0}main{max-width:1050px;margin:auto;padding:32px 18px}h1{font-size:36px}.notice{background:#fff1cc;padding:16px;border-radius:8px}table{width:100%;background:white;border-collapse:collapse}th,td{padding:14px;border-bottom:1px solid #dce6ee;text-align:left;vertical-align:top}code{overflow-wrap:anywhere;white-space:normal}input{font:inherit;padding:12px;width:100%;box-sizing:border-box;margin:16px 0}summary{cursor:pointer;color:#255f9d}@media(max-width:650px){table{font-size:13px}th,td{padding:8px}}</style><main><h1>Claude Protein Design</h1><p>GFP variant prioritisation · METHOD</p><p class="notice">NOTICE</p><label for="query">Filter substitutions or hypotheses</label><input id="query" type="search" placeholder="Search a position or substitution"><table><thead><tr><th>Rank</th><th>Substitutions</th><th>Priority score</th><th>Hypothesis and sequence</th></tr></thead><tbody>ROWS</tbody></table><p>The reference is the exact ProteinGym GFP assay sequence. Positions 65–67 are protected. Sequence validity does not establish biological improvement.</p></main><script>document.getElementById("query").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(q));});</script></html>'
    (destination / "review.html").write_text(page.replace("METHOD", html.escape(ranking["method"])).replace("NOTICE", html.escape(notice)).replace("ROWS", rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run the offline pipeline with synthetic assay labels.")
    demo.add_argument("--output", type=Path, default=Path("outputs/demo"))
    proposal = commands.add_parser("propose", help="Propose sequence-valid GFP variants.")
    proposal.add_argument("--provider", choices=["random", "claude"], default="random")
    proposal.add_argument("--count", type=int, default=20)
    proposal.add_argument("--seed", type=int, default=42)
    proposal.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", ""))
    proposal.add_argument("--output", type=Path, required=True)
    prepare = commands.add_parser("prepare", help="Prepare measured candidates without revealing assay labels to ranking.")
    prepare.add_argument("--assay", type=Path, required=True)
    prepare.add_argument("--count", type=int, default=200)
    prepare.add_argument("--seed", type=int, default=42)
    prepare.add_argument("--data-kind", choices=["synthetic", "published"], required=True)
    prepare.add_argument("--output", type=Path, required=True)
    rank = commands.add_parser("rank", help="Rank supplied candidates using a baseline or Claude.")
    rank.add_argument("--input", type=Path, required=True)
    rank.add_argument("--provider", choices=["distance", "random", "claude"], default="distance")
    rank.add_argument("--seed", type=int, default=42)
    rank.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", ""))
    rank.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser("evaluate", help="Evaluate ranked, measured candidates against a separate assay CSV.")
    evaluate.add_argument("--ranking", type=Path, required=True)
    evaluate.add_argument("--assay", type=Path, required=True)
    evaluate.add_argument("--top-k", type=int, default=10)
    evaluate.add_argument("--hit-threshold", type=float, default=None)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        config = load_reference()
        if args.command == "demo":
            save_json(args.output / "unmeasured_proposals.json", propose(config, "random", 12, 42))
            candidates = prepare_benchmark(ROOT / "data/synthetic_assay.csv", config, 20, 42, "synthetic")
            save_json(args.output / "benchmark_candidates.json", candidates)
            ranking = rank_candidates(candidates, config, "distance", 42)
            export_ranking(ranking, args.output)
            save_json(args.output / "evaluation.json", evaluate_ranking(ranking, ROOT / "data/synthetic_assay.csv", config, 3, None))
            print(f"Synthetic software demo completed: {args.output}")
        elif args.command == "propose":
            save_json(args.output, propose(config, args.provider, args.count, args.seed, args.model))
            print(f"Computational proposals saved: {args.output}")
        elif args.command == "prepare":
            save_json(args.output, prepare_benchmark(args.assay, config, args.count, args.seed, args.data_kind))
            print(f"Label-free candidate input saved: {args.output}")
        elif args.command == "rank":
            document = json.loads(args.input.read_text(encoding="utf-8"))
            if args.provider == "claude":
                print(f"Claude mode: up to {math.ceil(len(document['variants']) / 10)} paid requests; automatic retries disabled.", file=sys.stderr)
            export_ranking(rank_candidates(document, config, args.provider, args.seed, args.model), args.output)
            print(f"Ranking saved: {args.output}")
        else:
            ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
            save_json(args.output, evaluate_ranking(ranking, args.assay, config, args.top_k, args.hit_threshold))
            print(f"Evaluation saved: {args.output}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Provider failed ({type(exc).__name__}); no automatic paid retry was made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
