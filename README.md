# Claude Protein Design

**Claude-assisted design and prioritisation of green fluorescent protein variants.**

This research prototype asks whether Claude can propose and rank amino acid
substitutions that retain or increase GFP fluorescence. It combines constrained
variant generation, reproducible baselines, a local review report and evaluation
against separately supplied experimental assay measurements.

The biological case study is the GFP assay from Sarkisyan and colleagues (2016),
as represented in the official ProteinGym benchmark. The exact assay reference
sequence is included with source provenance. Its substitutions are checked using
that reference, rather than an interchangeable generic GFP sequence.

Maintainer: **Soh Jia Sheng**. Initial implementation and documentation were
prepared with AI assistance. This is an independent undergraduate prototype;
no confirmed supervisor or institutional endorsement is claimed.

## Research question

Can Claude improve the prioritisation of fluorescent-protein variants relative
to random ranking and a fewer-substitutions baseline, while producing valid
sequences, useful hypotheses and explicit uncertainty?

The target outcome is fluorescence in the supplied assay. A sequence-valid
candidate or a model's rationale does not establish improved folding, brightness,
chromophore maturation, stability or experimental success.

## Implemented now

- Generate constrained GFP substitution proposals using a seeded random baseline
  or optional Claude API integration.
- Preserve the reference length, the 20-amino-acid alphabet and positions 65–67.
  Apply a maximum of three substitutions within the configured assay region.
- Reject incorrect reference residues, repeated positions, indels and invalid
  model outputs. Record rejected design proposals.
- Prepare a blinded candidate pool from a ProteinGym-format assay CSV. Measured
  scores remain separate from the ranking input.
- Rank candidates with seeded random scores, mutation-distance scores or Claude.
- Export ranked candidates as JSON, CSV, FASTA and an interactive local HTML report.
- Evaluate measured candidates using tie-aware Spearman correlation, nDCG and
  top-k assay statistics.

**Twenty offline tests and a synthetic pipeline demonstration have been run.
No live Claude experiment, real-assay performance result or new laboratory
validation is claimed.**

## Run the offline demonstration

Requires Python 3.11 or later. No package installation or API key is needed:

```bash
python3 app.py demo --output outputs/demo
python3 -m unittest discover -s tests -v
```

Open `outputs/demo/review.html` locally. The report lets you inspect substitutions,
priority scores, uncertainty and full candidate sequences.

A generated example is included at [examples/demo/review.html](examples/demo/review.html).
Download the HTML file and open it locally to view it. The toy assay scores are
explicitly synthetic and do not describe actual GFP measurements.

## Propose protein variants

```bash
python3 app.py propose --provider random --count 20 --seed 42 --output outputs/proposals.json
python3 app.py rank --input outputs/proposals.json --provider distance --output outputs/proposal-ranking
```

These are unmeasured design candidates. Evaluation requires actual measurements
for every candidate; the application will not fill in missing assay scores.
For a realistic initial comparison, rank an existing measured candidate pool
without revealing its assay labels to the model.

## Use a real GFP assay

Obtain `GFP_AEQVI_Sarkisyan_2016.csv` from the
[official ProteinGym data resources](https://github.com/OATML-Markslab/ProteinGym).
Place it in `private_data/`. The full assay is not bundled with this prototype.

```bash
python3 app.py prepare --assay private_data/GFP_AEQVI_Sarkisyan_2016.csv --count 200 --seed 42 --data-kind published --output outputs/benchmark-candidates.json
python3 app.py rank --input outputs/benchmark-candidates.json --provider distance --output outputs/distance
python3 app.py rank --input outputs/benchmark-candidates.json --provider random --seed 42 --output outputs/random
python3 app.py evaluate --ranking outputs/distance/ranking.json --assay private_data/GFP_AEQVI_Sarkisyan_2016.csv --top-k 20 --output outputs/distance-evaluation.json
```

The adapter verifies each mutated sequence against its mutation descriptor and
the included assay reference. It records eligible and excluded row counts, samples
without using assay scores, and retains the assay hash for later evaluation.
Canonical duplicate variants must be explicitly aggregated upstream.

## Use Claude

Install the optional SDK and select an API model available to your Console
organisation. The application does not automatically load `.env` files.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-claude.txt
export ANTHROPIC_API_KEY="YOUR_API_KEY"
export ANTHROPIC_MODEL="YOUR_AVAILABLE_MODEL_ID"
python3 app.py propose --provider claude --count 10 --output outputs/claude-proposals.json
python3 app.py rank --input outputs/benchmark-candidates.json --provider claude --output outputs/claude-ranking
```

Check the [official Claude model catalogue](https://platform.claude.com/docs/en/models/overview)
for available model IDs. Live mode sends reference/candidate sequences to Anthropic
and consumes API credits. Scoring uses batches of up to ten candidates. Model IDs,
prompt hashes and token usage are recorded. Automatic SDK retries are disabled.

A malformed or incomplete scoring response stops the command. Earlier successful
API calls may already have consumed credits. This initial version does not retain
partial ranking results after a failed command. Score calibration across batches
is a research limitation, not an established property of the method.

## Evaluation definitions

| Measure | Definition |
| --- | --- |
| Spearman | Rank correlation with average ranks for tied values; undefined for a constant ranking |
| nDCG at k | Linear relevance equals the assay score minus the pool minimum; ties use canonical variant ID |
| Top-k mean | Mean measured DMS score of the selected candidates |
| Top-k hit rate | Optional fraction meeting a user-supplied `--hit-threshold` |

Predicted priority scores are not calibrated probabilities or measured fluorescence.
The distance baseline favours fewer substitutions and is deliberately simple.
Neither baseline models structure or epistasis. Comparisons with protein-specific
models and biological testing are proposed in the research plan.

## Research documents

- [Research plan](docs/RESEARCH_PLAN.md): study design, baselines and six-month milestones.
- [Application draft](docs/APPLICATION_DRAFT.md): proposal text for AI for Science.
- [Validation record](docs/VALIDATION.md): completed software checks and remaining experiments.
- [Data provenance](data/README.md): the real reference sequence and synthetic test labels.

## Programme fit

Anthropic's [AI for Science programme](https://support.claude.com/en/articles/11199177-anthropic-s-ai-for-science-program)
particularly prioritises biology and life sciences. This proposal studies protein
engineering and uses Claude for repeatable design and prioritisation experiments.
Programme acceptance also depends on scientific merit, feasibility, credentials
and institutional research attachment.

## References and licensing

1. Sarkisyan and colleagues (2016), *Local fitness landscape of the green
   fluorescent protein*, Nature. [DOI: 10.1038/nature17995](https://doi.org/10.1038/nature17995).
2. Notin and colleagues (2023), *ProteinGym: Large-Scale Benchmarks for Protein
   Fitness Prediction and Design*.
   [Official paper](https://papers.nips.cc/paper_files/paper/2023/hash/cac723e5ff29f65e3fcbb0739ae91bee-Abstract-Datasets_and_Benchmarks.html)
   and [code/data resources](https://github.com/OATML-Markslab/ProteinGym).

Original project code uses MIT licensing. The included ProteinGym reference
metadata is attributed in `data/reference.json`; its upstream MIT notice is
retained in `data/PROTEINGYM_LICENSE.txt`. Source publication rights remain with
their respective owners.
